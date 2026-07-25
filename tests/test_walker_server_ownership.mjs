// Self-serve protocol-walker server ownership tests.
//
// These are deliberately Node-only: no browser or protocol page is needed to
// prove that a self-served run owns the server it reaches.

import assert from "node:assert/strict";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { REPO_ROOT } from "./playwright/repo_root.mjs";
import { startOwnedStaticServer, stopOwnedStaticServer } from "./playwright/e2e/walker_server.mjs";

function createStaticDirectory() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "walker_server_"));
  fs.writeFileSync(path.join(directory, "index.html"), "<p>owned walker server</p>");
  return directory;
}

async function listenOnEphemeralPort(server) {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (typeof address !== "object" || address === null) {
    throw new Error("test listener did not expose a TCP address");
  }
  return address.port;
}

test("walker self-serve uses an OS-assigned port owned by its child", async () => {
  const directory = createStaticDirectory();
  let ownedServer = null;
  try {
    ownedServer = await startOwnedStaticServer({
      port: 0,
      directory,
      cwd: REPO_ROOT,
    });
    const response = await fetch(`${ownedServer.baseUrl}/index.html`);
    assert.equal(response.status, 200);
    assert.match(await response.text(), /owned walker server/);
  } finally {
    if (ownedServer !== null) {
      await stopOwnedStaticServer(ownedServer.child);
    }
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("walker rejects an explicitly occupied self-serve port before navigation", async () => {
  const directory = createStaticDirectory();
  const occupiedServer = net.createServer();
  try {
    const port = await listenOnEphemeralPort(occupiedServer);
    await assert.rejects(
      startOwnedStaticServer({
        port,
        directory,
        cwd: REPO_ROOT,
      }),
      /owned static server failed to start/,
    );
  } finally {
    await new Promise((resolve) => occupiedServer.close(resolve));
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
