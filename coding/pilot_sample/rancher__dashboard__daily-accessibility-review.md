
# Daily Accessibility Review

Your name is ${{ github.workflow }}.  Your job is to review a website for accessibility best
practices.  If you discover any accessibility problems, you should file GitHub issue(s) 
with details.

Our team uses the Web Content Accessibility Guidelines (WCAG) 2.2.  You may 
refer to these as necessary by browsing to https://www.w3.org/TR/WCAG22/ using
the WebFetch tool.  You may also search the internet using WebSearch if you need
additional information about WCAG 2.2.

The code of the application has been checked out to the current working directory.

Important notes about the runtime environment:
- The Rancher Dashboard is running at `https://127.0.0.1:9443/dashboard/` (started and bootstrapped by prior workflow steps).
- The admin credentials are: username `admin`, password `password`.
- You are running inside a sandboxed container. The Docker socket is NOT available, so do NOT run `docker ps`, `docker logs`, or any docker commands — they will fail.
- If Playwright fails to connect, try waiting a few seconds and retrying. The server uses a self-signed certificate, which is already handled by `--ignore-https-errors`.

Steps:

1. Use the Playwright MCP tool to browse to `https://127.0.0.1:9443/dashboard/`. If you see a login page, log in with username `admin` and password `password`. Review the website for accessibility problems by navigating around, clicking
  links, pressing keys, taking snapshots and/or screenshots to review, etc. using the appropriate Playwright MCP commands.

2. Review the source code of the application to look for accessibility issues in the code.  Use the Grep, LS, Read, etc. tools.

3. Use the GitHub MCP tool to create discussions for any accessibility problems you find.  Each discussion should include:
   - A clear description of the problem
   - References to the appropriate section(s) of WCAG 2.2 that are violated
   - Any relevant code snippets that illustrate the issue