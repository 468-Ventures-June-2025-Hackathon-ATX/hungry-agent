from typing import Awaitable, Callable
from browser_use import Agent, Browser, BrowserConfig
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import warnings
import os

load_dotenv()

warnings.filterwarnings("ignore")

# Set a custom config directory that we have permissions for
os.environ['BROWSERUSE_CONFIG_DIR'] = '/tmp/browseruse'
os.makedirs('/tmp/browseruse', exist_ok=True)

# Initialize browser config
browser_config = BrowserConfig(
    chrome_instance_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS path
    headless=False,  # Run in visible mode for debugging
    chrome_args=[
        '--no-default-browser-check',
        '--disable-default-apps', 
        '--no-first-run',
        '--disable-extensions',
        '--disable-session-crashed-bubble',
        '--disable-infobars',
        '--start-maximized',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
    ]
)

llm = ChatAnthropic(model_name="claude-3-5-sonnet-latest")

task_template = """
perform the following task
{task}
"""

async def run_browser_agent(task: str, on_step: Callable[[], Awaitable[None]]):
    """Run the browser-use agent with the specified task."""
    import sys
    
    try:
        # Use the simple Agent approach that works
        agent = Agent(
            task=task_template.format(task=task),
            llm=llm,
        )

        # Send progress updates to stderr so they don't interfere with JSON-RPC
        print(f"🤖 Starting browser automation for task: {task[:100]}...", file=sys.stderr)
        result = await agent.run()
        print(f"✅ Browser automation completed successfully!", file=sys.stderr)
        
        return result.final_result()
        
    except Exception as e:
        print(f"❌ Browser automation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise e
