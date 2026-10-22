# Test execution and aggregation sample

Minimal downstream project that runs iets3 tests headless (no MPS IDE) via Gradle - interpreted tests, generated
JUnit tests and model checks - and aggregates the results in GitHub Actions with links that open the failing node
in a running MPS.

## Usage

```
./gradlew setup                        # download MPS, JBR and dependencies (versions: gradle/libs.versions.toml)
./gradlew runInterpretedTests          # case 1: interpret user models, nothing is built
./gradlew runInterpretedLanguageTests  # case 2: build the project's own language, then interpret its tests
./gradlew runGeneratedTests            # generate the tests to JUnit classes, compile and run them
./gradlew checkModels                  # model checker
./gradlew check                        # all of the above
./gradlew runFailingInterpretedTests   # demo: TestExecutionSample.failingTests contains a broken test, fails on purpose
./gradlew runFailingGeneratedTests     # demo: TestExecutionSample.generatedFailingTests, fails on purpose
./gradlew --continue runAllTests       # everything incl. the demos in one run; always fails as the demos fail
```

Results: `build/test-results/<task>/` (`interpreted-*`, `generated*`, `checkmodels`). A task fails on test failures or if no results were written.

## How it works

The build model `mpsModules/solutions/buildScripts` contains an `InterpreterTestRunnerAspect` per case. Its
generated ant script (`run-interpreted-*.xml`) starts MPS headless, loads the modules from its `path` entries and
interprets all tests found there. Its required output folder receives the JUnit XML results.

- `TestExecutionSample.tests` uses published iets3 languages only
- `TestExecutionSample.languageTests` uses the project's own language `TestExecutionSample`, which has to
  be compiled first (`buildLanguages`)

After changing the build model, regenerate the ant scripts in MPS (rebuild `buildScripts`).
