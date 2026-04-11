#!/bin/bash
cd /opt/mcp-servers/qdrant-knowledge
INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
NOTIF='{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'
CALL='{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_knowledge","arguments":{"query":"n8n workflow knowledge ingestion pipeline setup homelab","project":"homelab","limit":3}}}'
INIT_LEN=${#INIT}
NOTIF_LEN=${#NOTIF}
CALL_LEN=${#CALL}
echo "LENS: $INIT_LEN / $NOTIF_LEN / $CALL_LEN"
(printf "Content-Length: $INIT_LEN\r\n\r\n$INIT"; sleep 2; printf "Content-Length: $NOTIF_LEN\r\n\r\n$NOTIF"; sleep 2; printf "Content-Length: $CALL_LEN\r\n\r\n$CALL"; sleep 15) | timeout 25 node qdrant-mcp-server.js > /tmp/out.txt 2>/tmp/err.txt
echo "=== STDERR ==="
cat /tmp/err.txt
echo "=== STDOUT ==="
cat /tmp/out.txt
