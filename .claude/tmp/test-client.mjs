import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: "node",
  args: ["qdrant-mcp-server.js"],
  cwd: "/opt/mcp-servers/qdrant-knowledge"
});

const client = new Client({ name: "test-client", version: "1.0" });

try {
  console.error("Connecting...");
  await client.connect(transport);
  console.error("Connected. Calling search_knowledge...");

  const result = await client.callTool({
    name: "search_knowledge",
    arguments: {
      query: "n8n workflow knowledge ingestion pipeline setup",
      project: "homelab",
      limit: 3
    }
  });

  console.error("=== TOOL RESULT ===");
  console.error(JSON.stringify(result, null, 2));
} catch (e) {
  console.error("ERROR:", e.message);
} finally {
  await client.close();
}
