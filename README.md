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
./gradlew runFailingInterpretedTests   # demo: libre.mps.testsample.interpreted.noBuild.failing contains a broken test
./gradlew runFailingInterpretedLanguageTests  # demo: builds the own language, libre.mps.testsample.interpreted.build.failing
./gradlew runFailingGeneratedTests     # demo: libre.mps.testsample.generated.failing contains a broken test
./gradlew checkFailingModels           # demo: libre.mps.testsample.modelcheck.failing has a model check error and warning
./gradlew --continue runAllTests       # everything incl. the demos in one run; always fails as the demos fail
```

Results: `build/test-results/<run>/`. A task fails on test failures or if no results were written.

Each run has one name throughout: report heading, results folder, ant script `run-<run>.xml`, build project
`libre.mps.testsample.<run>` and the MPS module it tests:

| Run | Gradle task | MPS module |
|---|---|---|
| `runCheckModels` | `checkModels` | all modules except `libre.mps.testsample.modelcheck.failing` |
| `runCheckModels-failing` | `checkFailingModels` | `libre.mps.testsample.modelcheck.failing` |
| `runInterpretedTests-no-build` | `runInterpretedTests` | `libre.mps.testsample.interpreted.noBuild` |
| `runInterpretedTests-build` | `runInterpretedLanguageTests` | `libre.mps.testsample.interpreted.build` |
| `runInterpretedTests-no-build-failing` | `runFailingInterpretedTests` | `libre.mps.testsample.interpreted.noBuild.failing` |
| `runInterpretedTests-build-failing` | `runFailingInterpretedLanguageTests` | `libre.mps.testsample.interpreted.build.failing` |
| `runGeneratedTests` | `runGeneratedTests` | `libre.mps.testsample.generated` |
| `runGeneratedTests-failing` | `runFailingGeneratedTests` | `libre.mps.testsample.generated.failing` |

The test models are named `<module>.tests` (generated: `<module>.tests@tests`).

## How it works

The build model `mpsModules/solutions/libre.mps.testsample.build` contains an `InterpreterTestRunnerAspect` per case. Its
generated ant script (`run-runInterpretedTests-*.xml`) starts MPS headless, loads the modules from its `path` entries and
interprets all tests found there. Its required output folder receives the JUnit XML results.

- `libre.mps.testsample.interpreted.noBuild` uses published iets3 languages only
- `libre.mps.testsample.interpreted.build` uses the project's own language `libre.mps.testsample`, which has to
  be compiled first (`buildLanguages`)

After changing the build model, regenerate the ant scripts in MPS (rebuild `libre.mps.testsample.build`) or run `./gradlew buildScripts`.
