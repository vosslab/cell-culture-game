// Owned static-server lifecycle for the schema-driven protocol walker.
//
// Self-serve mode must prove that the child it created bound the port before a
// browser navigates. A reachable URL alone is not proof of ownership: another
// local server might already answer there.

import { spawn } from "node:child_process";

const STARTUP_TIMEOUT_MS = 5000;

// Use the OS-assigned ephemeral port in the normal self-serve case. An
// explicitly supplied --port or PORT value remains an intentional override.
export function resolveSelfServePort(explicitPort, envPort = process.env.PORT) {
  if (explicitPort !== null) {
    return explicitPort;
  }
  if (envPort !== undefined && envPort !== "") {
    const parsedPort = Number.parseInt(envPort, 10);
    if (Number.isInteger(parsedPort) && parsedPort >= 1 && parsedPort <= 65535) {
      return parsedPort;
    }
  }
  return 0;
}

function readReadyPort(output) {
  const readyMatch = output.match(/Serving HTTP on .* port (\d+) \(/);
  if (readyMatch === null) {
    return null;
  }
  const readyPort = Number.parseInt(readyMatch[1], 10);
  if (!Number.isInteger(readyPort) || readyPort < 1 || readyPort > 65535) {
    return null;
  }
  return readyPort;
}

function buildStartupFailure(output, detail) {
  const cleanOutput = output.trim();
  const suffix = cleanOutput === "" ? "" : ` Output: ${cleanOutput}`;
  const message = `owned static server failed to start: ${detail}.${suffix}`;
  const error = new Error(message);
  return error;
}

function waitForOwnedServer(child, requestedPort, timeoutMs) {
  return new Promise((resolve, reject) => {
    let output = "";
    let settled = false;

    function finish(callback, value) {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeoutId);
      callback(value);
    }

    function fail(detail) {
      const error = buildStartupFailure(output, detail);
      finish(reject, error);
    }

    function inspectOutput(chunk) {
      output += chunk.toString();
      const readyPort = readReadyPort(output);
      if (readyPort === null) {
        return;
      }
      if (requestedPort !== 0 && readyPort !== requestedPort) {
        fail(`requested port ${requestedPort}, but child reported port ${readyPort}`);
        return;
      }
      finish(resolve, readyPort);
    }

    const timeoutId = setTimeout(() => {
      fail(`timed out after ${timeoutMs}ms while binding port ${requestedPort}`);
    }, timeoutMs);

    child.stdout.on("data", inspectOutput);
    child.stderr.on("data", inspectOutput);
    child.once("error", (error) => {
      fail(`could not launch child process: ${error.message}`);
    });
    child.once("exit", (code, signal) => {
      fail(`child exited before readiness (code=${code}, signal=${signal})`);
    });
  });
}

export async function startOwnedStaticServer({
  port,
  directory,
  cwd,
  timeoutMs = STARTUP_TIMEOUT_MS,
}) {
  const child = spawn(
    "python3",
    ["-u", "-m", "http.server", String(port), "--bind", "127.0.0.1", "--directory", directory],
    {
      stdio: ["ignore", "pipe", "pipe"],
      cwd,
    },
  );

  try {
    const actualPort = await waitForOwnedServer(child, port, timeoutMs);
    const baseUrl = `http://127.0.0.1:${actualPort}`;
    return { child, port: actualPort, baseUrl };
  } catch (error) {
    await stopOwnedStaticServer(child);
    throw error;
  }
}

export function stopOwnedStaticServer(child) {
  if (child.exitCode !== null || child.killed) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    child.once("exit", resolve);
    child.kill();
  });
}
