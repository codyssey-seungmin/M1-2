import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { dirname, extname, join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";

const dist = join(dirname(fileURLToPath(import.meta.url)), "dist");
const host = "127.0.0.1";
const port = Number(process.env.FRONTEND_PORT || 5500);
const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
};

createServer(async (request, response) => {
  const path = normalize(
    decodeURIComponent(new URL(request.url, `http://${host}:${port}`).pathname),
  );
  const file = join(
    dist,
    path === sep ? "index.html" : path.replace(/^[\\/]+/, ""),
  );
  if (!file.startsWith(dist + sep)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }
  try {
    const data = await readFile(file);
    response.writeHead(200, {
      "Content-Type": mime[extname(file)] || "application/octet-stream",
    });
    response.end(data);
  } catch {
    response.writeHead(404);
    response.end("Not found");
  }
}).listen(port, host, () =>
  console.log(`Pageful preview: http://${host}:${port}`),
);
