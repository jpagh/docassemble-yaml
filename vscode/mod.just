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

test: build
    npm test

test-real: build
    DOCASSEMBLE_LSP_ENABLE_REAL_TEST=1 npm test

watch:
    npm run watch
