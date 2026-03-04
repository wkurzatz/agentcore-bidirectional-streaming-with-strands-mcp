"""Bedrock AgentCore Runtime - Main agent application."""

import os
import sys
import traceback

from bedrock_agentcore import BedrockAgentCoreApp
from starlette.websockets import WebSocketDisconnect
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from pydantic import AnyUrl

# Add parent directory to path for utils import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import logger, handle_server_error, handle_validation_error

# MCP Server Configuration - path to the DPD server
MCP_SERVER_PATH = os.environ.get("MCP_SERVER_PATH", r"C:\Users\g452\Documents\git\PharmacyMCP")
MCP_SERVER_PYTHON = os.environ.get("MCP_SERVER_PYTHON", r"C:\Users\g452\Documents\git\PharmacyMCP\.venv\Scripts\python.exe")


def log_environment():
    """Log environment variables for debugging."""
    logger.info("=" * 50)
    logger.info("Agent startup initiated")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"MCP Server Path: {MCP_SERVER_PATH}")
    logger.info(f"MCP Server Python: {MCP_SERVER_PYTHON}")
    
    
    # Log environment variables (mask sensitive values)
    logger.info("Environment variables:")
    for key in ['AWS_REGION', 'AWS_DEFAULT_REGION', 'BEDROCK_MODEL_ID', 'AWS_EXECUTION_ENV']:
        logger.info(f"  {key}={os.environ.get(key, 'NOT SET')}")
    
    # Check if credentials are available (don't log actual values)
    logger.info(f"  AWS_ACCESS_KEY_ID={'SET' if os.environ.get('AWS_ACCESS_KEY_ID') else 'NOT SET'}")
    logger.info(f"  AWS_SECRET_ACCESS_KEY={'SET' if os.environ.get('AWS_SECRET_ACCESS_KEY') else 'NOT SET'}")
    logger.info(f"  AWS_SESSION_TOKEN={'SET' if os.environ.get('AWS_SESSION_TOKEN') else 'NOT SET'}")


BASE_SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to the Health Canada Drug Product Database (DPD). "
    "You can help users search for drug information, including active ingredients, company details, "
    "dosage forms, and more."
)

# Reference resources to pre-load into the system prompt
REFERENCE_RESOURCES = [
    "dpd://reference/status-codes",
    "dpd://reference/schedules",
    "dpd://reference/routes",
]


def fetch_resource(uri: str) -> str:
    """Fetch a resource from the MCP server by URI and return its text content."""
    async def _read():
        result = await mcp_client._background_thread_session.read_resource(AnyUrl(uri))
        return "\n".join(
            content.text for content in result.contents if hasattr(content, "text")
        )
    return mcp_client._invoke_on_background_thread(_read()).result()


def build_system_prompt() -> str:
    """Build the system prompt, enriched with reference data from MCP resources."""
    sections = [BASE_SYSTEM_PROMPT, "\n\n---\n"]
    for uri in REFERENCE_RESOURCES:
        try:
            content = fetch_resource(uri)
            sections.append(content)
            logger.info(f"Loaded reference resource: {uri}")
        except Exception as e:
            logger.warning(f"Could not load resource {uri}: {e}")
    return "\n".join(sections)


def create_agent(tools=None):
    """Create and configure the Bedrock agent."""
    model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    logger.info(f"Creating BedrockModel with model_id={model_id}, region={region}")
    
    try:
        bedrock_model = BedrockModel(
            model_id=model_id,
            region_name=region
        )
        logger.info("BedrockModel created successfully")
    except Exception as e:
        logger.error(f"Failed to create BedrockModel: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    
    try:
        system_prompt = build_system_prompt()
        logger.info(f"System prompt built ({len(system_prompt)} chars)")
        agent = Agent(
            model=bedrock_model,
            tools=tools or [],
            system_prompt=system_prompt
        )
        logger.info(f"Agent created successfully with {len(tools) if tools else 0} MCP tools")
        return agent
    except Exception as e:
        logger.error(f"Failed to create Agent: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


# Log environment on module load
log_environment()

# Initialize the AgentCore app
logger.info("Initializing BedrockAgentCoreApp...")
app = BedrockAgentCoreApp()
logger.info("BedrockAgentCoreApp initialized")

# Create the MCP client for Health Canada DPD API (stdio transport)
logger.info(f"Starting MCP server via stdio from {MCP_SERVER_PATH}...")
mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(
        command=MCP_SERVER_PYTHON,
        args=["-m", "src.dpd_server"],
        cwd=MCP_SERVER_PATH
    )
))
mcp_client.start()

# Get tools from the MCP server
mcp_tools = mcp_client.list_tools_sync()
logger.info(f"Discovered {len(mcp_tools)} tools from MCP server:")
for tool in mcp_tools:
    logger.info(f"  - {tool.tool_name}: {tool.tool_spec.get('description', 'No description')[:80]}")

# Create the agent with MCP tools
agent = create_agent(tools=mcp_tools)


@app.websocket
async def websocket_handler(websocket, context):
    """
    Handles bidirectional streaming.
    The client stays connected for multiple questions.
    """
    logger.debug(f"WebSocket connection attempt, context: {context}")
    
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        print("WebSocket connection accepted")
    except Exception as e:
        print(f"Failed to accept WebSocket: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Failed to accept WebSocket: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    
    try:
        while True:
            # 1. Receive the next question from the client
            logger.debug("Waiting for message...")
            message = await websocket.receive_json()
            logger.debug(f"Received message: {message}")
            user_prompt = message.get("prompt")
            
            if not user_prompt:
                logger.debug("No prompt in message, skipping")
                error_response = handle_validation_error("No prompt provided")
                await websocket.send_json({"type": "error", **error_response})
                continue

            print(f"Processing prompt: {user_prompt[:100]}...")
            logger.info(f"Processing prompt: {user_prompt[:100]}...")

            # 2. Stream the response from the LLM back to the client
            logger.debug("Starting stream_async...")
            chunk_count = 0
            try:
                async for event in agent.stream_async(user_prompt):
                    chunk_count += 1
                    content = event.get("data", "")
                    if chunk_count <= 3:
                        logger.debug(f"Chunk {chunk_count}: {repr(content[:50]) if content else 'empty'}")
                    # Send keepalive-friendly chunks
                    await websocket.send_json({
                        "type": "chunk",
                        "content": content
                    })
                print(f"Streaming complete, sent {chunk_count} chunks")
                logger.info(f"Streaming complete, sent {chunk_count} chunks")
            except Exception as e:
                print(f"\n*** ERROR during streaming: {e}")
                print(f"*** Traceback:\n{traceback.format_exc()}")
                logger.error(f"Error during streaming: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                try:
                    error_response = handle_server_error(str(e))
                    await websocket.send_json({"type": "error", **error_response})
                except Exception as send_err:
                    print(f"*** Failed to send error response: {send_err}")
                    logger.error(f"Failed to send error response: {send_err}")
                continue
            
            # 3. Send an end-of-turn signal so the client knows the answer is finished
            await websocket.send_json({"type": "end_of_turn"})
            logger.debug("Sent end_of_turn signal")
            
    except WebSocketDisconnect:
        print("Client disconnected")
        logger.info("Client disconnected")
    except Exception as e:
        print(f"\n*** Connection closed or error: {e}")
        print(f"*** Traceback:\n{traceback.format_exc()}")
        logger.error(f"Connection closed or error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        print("WebSocket handler exiting")
        logger.info("WebSocket handler exiting")


if __name__ == "__main__":
    logger.info("Starting server...")
    print("Server started successfully!")
    app.run()
