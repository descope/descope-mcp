# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/descope/descope-mcp/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                             |    Stmts |     Miss |   Cover |   Missing |
|--------------------------------- | -------: | -------: | ------: | --------: |
| src/descope\_mcp/\_\_init\_\_.py |        8 |        0 |    100% |           |
| src/descope\_mcp/client.py       |      104 |       79 |     24% |26-27, 31-32, 36, 40-45, 49-51, 76-88, 111-122, 145-155, 176-185, 200-219, 233-248, 260, 270, 277-318, 322 |
| src/descope\_mcp/connections.py  |       61 |       37 |     39% |13-14, 106-114, 118-164, 171, 180, 203-204 |
| src/descope\_mcp/descope\_mcp.py |      238 |       97 |     59% |52-60, 82, 108-109, 136-141, 149, 244, 297, 323, 438, 507-513, 559, 573, 593-604, 656-702, 723-724, 737-738, 783-798, 810-825, 843, 849, 878, 884-887, 905, 911, 937, 943-946, 960-962, 1000-1018 |
| src/descope\_mcp/server.py       |      121 |       98 |     19% |40-71, 75-160, 164-178, 186-215, 221-245, 253-277, 283-308, 314-315, 338, 343-358, 362 |
| src/descope\_mcp/session.py      |       82 |       23 |     72% |65, 80-82, 189, 210, 217-226, 278-279, 282, 334, 396-416 |
| src/descope\_mcp/types.py        |       24 |        0 |    100% |           |
|                        **TOTAL** |  **638** |  **334** | **48%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/descope/descope-mcp/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/descope/descope-mcp/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/descope/descope-mcp/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/descope/descope-mcp/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fdescope%2Fdescope-mcp%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/descope/descope-mcp/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.