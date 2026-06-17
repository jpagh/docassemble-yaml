build:
    npm run build

compile:
    npm run compile

publish:
    npm run build
    vsce package
    vsce publish

test: build
    npm test

test-real: build
    DOCASSEMBLE_LSP_ENABLE_REAL_TEST=1 npm test

watch:
    npm run watch
