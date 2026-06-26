build:
    npm run build

compile:
    npm run compile

package:
    npm run build
    npx @vscode/vsce package

publish:
    npm run build
    npx @vscode/vsce package
    npx @vscode/vsce publish

# Run VS Code extension tests against real docassemble-lsp
test: build
    DOCASSEMBLE_LSP_ENABLE_REAL_TEST=1 node ./dist/test/runTest.js

# Run VS Code extension tests against mock lsp
test-mock: build
    node ./dist/test/runTest.js

watch:
    npm run watch
