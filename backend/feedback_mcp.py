"""A bounded MCP host: only the app's own three read-only tools can be called."""
import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .feedback_context import ContextRepository, fingerprint

TOOLS=('review_snapshot','find_writing_guidance','check_response_contract')

async def retrieve(root,database,job_id):
    params=StdioServerParameters(command=sys.executable,args=['-m','backend.tutor_mcp','--data-dir',str(database.parent)],cwd=str(root))
    async with asyncio.timeout(15):
        with open(os.devnull,'w') as errlog:
            async with stdio_client(params,errlog=errlog) as (read,write):
                async with ClientSession(read,write,read_timeout_seconds=10) as session:
                    initialized=await session.initialize()
                    inventory=await session.list_tools()
                    if set(t.name for t in inventory.tools)!=set(TOOLS):raise ValueError('Unexpected tools in the tutor context service.')
                    out={};calls=[]
                    for name in TOOLS:
                        r=await session.call_tool(name,arguments={'job_id':job_id})
                        if r.is_error:raise ValueError('The tutor context tool could not supply the saved review.')
                        value=r.structured_content
                        if value is None:
                            value=json.loads(next(c.text for c in r.content if c.type=='text'))
                        out[name]=value
                        calls.append({'tool':name,'arguments':{'job_id':job_id},'result_hash':fingerprint(value)})
    hashes={value['snapshot_hash'] for value in out.values()}
    if len(hashes)!=1:raise ValueError('Context changed between tool calls. Request a new review.')
    return {'snapshot':out[TOOLS[0]],'guidance':out[TOOLS[1]],'contract':out[TOOLS[2]],
            'transport':'mcp-stdio','protocol_version':initialized.protocol_version,'tool_calls':calls}

async def retrieve_with_fallback(root,database,job_id):
    try:return await retrieve(root,database,job_id)
    except asyncio.CancelledError:raise
    except Exception:
        # Same read-only repository, not invented or partial model context.
        repo=ContextRepository(root,database)
        s=repo.snapshot(job_id);g=repo.guidance(job_id);c=repo.response_contract(job_id)
        if len({s['snapshot_hash'],g['snapshot_hash'],c['snapshot_hash']})!=1:raise ValueError('The saved context changed. Request a new review.')
        return {'snapshot':s,'guidance':g,'contract':c,'transport':'direct-local-fallback','tool_calls':[],
                'notice':'The MCP connection was unavailable. The same saved context and guidance were read directly on this Mac.'}
