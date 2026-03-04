# Sources
[thread in slack about MCP server release](https://anaconda.slack.com/archives/C08NHTGN277/p1772027749373659)
[epic](https://anaconda.atlassian.net/browse/DESK-864)
[PRD user stories](https://docs.google.com/document/d/1BPLKVWsqnZ_emwuePg9HED42u4V0n_e4BGiNm7I47Jw/edit?usp=sharing)

# Announcement
Huge moment... we're ready for some internal testing of Anaconda MCP in Claude Desktop :claude-spin::rocket:

The full set of docs and instructions can be found in Github here.  But the simple way is to run these three commands in a terminal:


Create a conda env with the MCP installed: conda create --name anaconda-mcp-testing -c datalayer -c anaconda-cloud/label/dev -c defaults -c conda-forge --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' anaconda-mcp=0.1.1
Activate the env: conda activate anaconda-mcp-testing 
Add the MCP tool to Claude Desktop: anaconda-mcp claude-desktop setup-config 


Restart Claude Desktop (CMD+Q) and you should have access to the following tools:


List conda environments
Create new conda environment
Install package to existing conda environment
Remove package from existing conda environment
Delete conda environment


Obviously there are more tools on the way, this is just the start!  For now we are mainly looking to test the install process, and make sure that you are able to call the right tools.  So start out by asking Claude to List all of my conda environments   and if it responds correctly that is ideal!

Sharing in this channel first with the aim of getting the whole @desktop-team to test it before sharing wider. Friends of Desktop also welcome though :slightly_smiling_face:

Shout out to @Romulo and @Eric Charles (Notebooks) who have done the bulk of this work, but kudos to everyone else who has helped us along the way :muscle: (edited)

# Conversation

Josh (Preston, UK)  [9:24 AM]
Small typo in the create env command, just need a space between the end quote of the channel name and the package name at the end :slightly_smiling_face:

Otherwise works great!
[9:26 AM]Interestingly I had to specify that I wanted to use the anaconda-mcp rather than just "List conda environments".

It wanted to keep using the browser MCP i have installed. My guess this is just a side effect of having too many tools enabled and it not being sure which it should actually use
Jack Evans  [9:29 AM]
Yes - hitting the right tool is challenging. If you disable anaconda-mcp and try it you will see it try and run conda commands which will fail too
Josh (Preston, UK)  [9:29 AM]
I managed to get it to work by disabling some of the more generic tools I have and it works without specifying now :slightly_smiling_face:
Julian U.  [9:42 AM]
Let's go :rocket:
Jack Evans  [9:30 AM]
Reposting this - @desktop-team please all give this a go so that we can move on to wider testing ASAP
Nick Beerbower (EST, he/him)  [9:50 AM]
Worked for me! But I did have to tell Claude to explicitly use the anaconda-mcp or else it tries to go off and use the claude chrome extension (for some reason?) and then use conda commands directly in a container
Jack Evans  [9:51 AM]
Even for basic commands like "Create a conda environment with pandas" ?
Nick Beerbower (EST, he/him)  [9:51 AM]
All i tried was List all of my conda environments
[9:52 AM]"Create a conda environment with pandas" went directly to the mcp!
Jack Evans  [9:53 AM]
interesting... thanks Nick
Nick Beerbower (EST, he/him)  [9:53 AM]
Did encounter this:
Screenshot 2026-02-26 at 9.53.33 AM.png Omar G. (EST)  [9:57 AM]
Encountered this during final step:
(anaconda-mcp-testing) ➜  ~ anaconda-mcp claude-desktop setup-config
Traceback (most recent call last):
  File "/opt/anaconda3/envs/anaconda-mcp-testing/bin/anaconda-mcp", line 3, in <module>
    from anaconda_mcp.cli import main
  File "/opt/anaconda3/envs/anaconda-mcp-testing/lib/python3.13/site-packages/anaconda_mcp/cli.py", line 28, in <module>
    from anaconda_mcp.utils import _render_config_template
  File "/opt/anaconda3/envs/anaconda-mcp-testing/lib/python3.13/site-packages/anaconda_mcp/utils.py", line 6, in <module>
    from anaconda_mcp.config import settings
  File "/opt/anaconda3/envs/anaconda-mcp-testing/lib/python3.13/site-packages/anaconda_mcp/config.py", line 50, in <module>
    settings = Settings()
  File "/opt/anaconda3/envs/anaconda-mcp-testing/lib/python3.13/site-packages/pydantic_settings/main.py", line 194, in __init__
    super().__init__(
    ~~~~~~~~~~~~~~~~^
        **__pydantic_self__._settings_build_values(
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<27 lines>...
        )
        ^
    )
    ^
  File "/opt/anaconda3/envs/anaconda-mcp-testing/lib/python3.13/site-packages/pydantic/main.py", line 250, in __init__
    validated_self = self.__pydantic_validator__.validate_python(data, self_instance=self)
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
openai_api_key
  Extra inputs are not permitted [type=extra_forbidden, input_value='sk-1ocPVZB52R1h81anGmV1T...kFJavBiHP7j6n8xWLSMvpgg', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/extra_forbidden
(anaconda-mcp-testing) ➜  ~Romulo  [9:59 AM]
@Nick Beerbower (EST, he/him) Could you share the conda list result? Wondering if this environment is nested
[10:00 AM]@Omar G. (EST) could you share your Claude Desktop config file? Perhaps you have some extra keys in there cc @Eric Charles (Notebooks)
Omar G. (EST)  [10:02 AM]
@Romulo
{
  "preferences": {
    "sidebarMode": "chat",
    "coworkScheduledTasksEnabled": false
  }
}claude_desktop_config.json 

{
  "preferences": {
    "sidebarMode": "chat",
    "coworkScheduledTasksEnabled": false
  }


Nick Beerbower (EST, he/him)  [10:13 AM]
{"is_error":false,"error_description":"","tool_result":{"environments":[{"name":"conda","path":"/Users/nbeerbower/.ai-navigator-alpha/conda"},{"name":"ai-nav-05c7fba0-0c9c-42f0-9a2e-9581c0670ebd","path":"/Users/nbeerbower/.ai-navigator-alpha/micromamba/envs/envs/ai-nav-05c7fba0-0c9c-42f0-9a2e-9581c0670ebd"},{"name":"ai-nav-demo","path":"/Users/nbeerbower/.ai-navigator-alpha/micromamba/envs/envs/ai-nav-demo"},{"name":"ai-nav-demo12346","path":"/Users/nbeerbower/.ai-navigator-alpha/micromamba/envs/envs/ai-nav-demo12346"},{"name":"ai-nav-test123","path":"/Users/nbeerbower/.ai-navigator-alpha/micromamba/envs/envs/ai-nav-test123"},{"name":"metal","path":"/Users/nbeerbower/.ai-navigator-alpha/micromamba/envs/metal"},{"name":"conda","path":"/Users/nbeerbower/.ai-navigator/conda"},{"name":"navigator","path":"/Users/nbeerbower/.ai-navigator/conda/envs/navigator"},{"name":"metal","path":"/Users/nbeerbower/.ai-navigator/micromamba/envs/metal"},{"name":"cpu","path":"/Users/nbeerbower/.anaconda-desktop-alpha/micromamba/envs/cpu"},{"name":"metal","path":"/Users/nbeerbower/.anaconda-desktop-alpha/micromamba/envs/metal"},{"name":"metal","path":"/Users/nbeerbower/.anaconda-desktop/micromamba/envs/metal"},{"name":"conda","path":"/Users/nbeerbower/AILauncher/ai-launcher/src/__tests__/temp/conda"},{"name":"navigator","path":"/Users/nbeerbower/AILauncher/ai-launcher/src/__tests__/temp/conda/envs/navigator"},{"name":"agents-api","path":"/Users/nbeerbower/agents-service/agents-api/env"},{"name":".package","path":"/Users/nbeerbower/anaconda-ai/.tox/.package"},{"name":"mypy","path":"/Users/nbeerbower/anaconda-ai/.tox/mypy"},{"name":"py310","path":"/Users/nbeerbower/anaconda-ai/.tox/py310"},{"name":"py311","path":"/Users/nbeerbower/anaconda-ai/.tox/py311"},{"name":"py312","path":"/Users/nbeerbower/anaconda-ai/.tox/py312"},{"name":"py39","path":"/Users/nbeerbower/anaconda-ai/.tox/py39"},{"name":"anaconda-ai","path":"/Users/nbeerbower/anaconda-ai/env"},{"name":"miniconda3","path":"/Users/nbeerbower/miniconda3"},{"name":"migrations","path":"/Users/nbeerbower/rbac/migrations/env"},{"name":"sisyphus","path":"/Users/nbeerbower/sisyphus/envs/sisyphus"},{"name":"anaconda3","path":"/opt/anaconda3"},{"name":"ana-test","path":"/opt/anaconda3/envs/ana-test"},{"name":"base","path":"/opt/anaconda3/envs/anaconda-mcp-testing"},{"name":"content-compare","path":"/opt/anaconda3/envs/content-compare"},{"name":"pandas-env","path":"/opt/anaconda3/envs/pandas-env"}]}}Augusto (Berlin - CET)  [10:52 AM]
I gave a test and had some findings.


Installed anaconda-mcp  following the instructions
then installed claude desktop
the changes were not applied, so I had to enable the Code execution and file creation on settings -> Capabilities
I restarted claude desktop couple of times and then worked the anaconda-mcp
I was able list my environments
Create an environment
Delete an environment was not fully possible (check images)
2 files Bruno (WET)  [11:19 AM]
I also had to manually enable Settings > Capabilities > Code execution and file creation > Cloud code execution and file creation  (and restart Claude) in order to use the mcp.


When listing the environments, the mcp correctly detected how many I had but is incorrectly classifying the anaconda-mcp-testing env as base .
When installing a package, the mcp could not find the specific environment by name. It had to search by path.
When removing an environment, the mcp stated that removal was complete, but when I checked, the environment was still present.
Every conda operation that ran for the first time manually required granting permission.


Besides the 4 points above, everything worked as expected :rocket: (edited) 
3 files Bruno (WET)  [11:27 AM]
Here are the screenshots for point (3) above. It should be noted that I had my-env activated in the cli when requesting its deletion from the mcp. (edited) 
2 files Yaroslav S (Kyiv - EET)  [12:34 PM]
On environments not being removed: looks like we found a potential root cause for that. Fix should be pushed to the repository tomorrow.
Romulo  [12:50 PM]
Very useful feedbacks here. Thanks a bunch for testing it!!!
Yaroslav S (Kyiv - EET)  [4:07 AM]
@Romulo I created a PR for the "environments not being removed" issue, can you, please, take a look at it (link). I also tried to modify existing tests to cover this aspect of environments being actually removed.
Romulo  [5:01 AM]
@Yaroslav S (Kyiv - EET) Looks solid, just approved your PR. Thanks for helping with it :high-five:
Jack Evans  [5:38 AM]
And this is why we dogfood :cool-doge: thanks all for testing.  @Romulo please shout when we're ready for Round 2 :bellhop_bell:
Romulo  [5:39 AM]
Sure thing. I have a solid amount of PRs opened that I want to get merged before releasing a new version.
Romulo  [10:42 AM]
I pushed new packages for Anaconda MCP and Environments MCP. Here is the updated command to create a new env:
conda create --name anaconda-mcp-testing -c datalayer -c anaconda-cloud/label/dev -c defaults -c conda-forge --channel 'https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/' anaconda-mcp=0.1.2 environments-mcp-server=0.1.7

In case you want to update your previously created environment:
conda install -c anaconda-cloud/label/dev anaconda-mcp=0.1.2 environments-mcp-server=0.1.7 -n anaconda-mcp-testing --force-reinstall
Maureen Murphy (Idaho - MT)  [2:26 PM]
I installed Anaconda MCP with the command Romulo just shared above, but I'm not able to create any new environments or add packages to my existing environments with Claude. Claude says the issue is specific to the repo.anaconda.cloud channel requiring credentials that the MCP tool isn't picking up. I'm able to list my environments, though.
Nick Beerbower (EST, he/him)  [2:34 PM]
Worked great for me! Created an environment with pandas, listed it, deleted it, and confirmed it was gone all with claude :slightly_smiling_face:
Omar G. (EST)  [2:37 PM]
On my end I'm still encountering the same previous error https://anaconda.enterprise.slack.com/archives/C08NHTGN277/p1772117866350999?thread_ts=1772027749.373659&cid=C08NHTGN277
Encountered this during final step:
(anaconda-mcp-testing) ➜  ~ anaconda-mcp claude-desktop setup-config
Traceback (most recent call last):
  File "/opt/anaconda3/envs/anaconda-mcp-testing/bin/anaconda-mcp", line 3, in <module>
    from anaconda_mcp.cli import main
From a thread in team-desktop | Feb 26th | View replyRomulo  [1:10 AM]
@Maureen Murphy (Idaho - MT) Thanks for the feedback. That error is something new to me, it would be great if we sync. Unfortunately, I am out sick today but we can find some time perhaps tomorrow.
[1:11 AM]@Omar G. (EST) I should have more clear, but the issue you have was not addressed in this new version. My bad! But thank you a lot for trying again.
Augusto (Berlin - CET)  [9:54 AM]
I’m also confirming that it’s possible to remove environments right now.
Maureen Murphy (Idaho - MT)  [9:59 AM]
@Romulo, sounds good. I'm OOO today as well, let's try to sync tomorrow!