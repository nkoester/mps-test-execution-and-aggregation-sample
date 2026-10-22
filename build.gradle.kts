import de.itemis.mps.gradle.BuildLanguages
import de.itemis.mps.gradle.RunAntScript
import de.itemis.mps.gradle.TestLanguages
import de.itemis.mps.gradle.tasks.MpsCheck
import kotlin.io.path.Path

buildscript {
    repositories {
        maven { url = uri("https://artifacts.itemis.cloud/repository/maven-mps/") }
    }
    dependencies {
        classpath(libs.mps.gradlePlugin)
    }
}

plugins {
    base
    alias(libs.plugins.mps.downloadJBR)
}
// misc paths
val buildPath = getLayout().buildDirectory.get().toString()
val mpsGenericPath = Path(buildPath, "/mps")
val dependencyInstallPath = Path(buildPath, "/dependencies")

repositories {
    mavenLocal()
    maven { url = uri("https://artifacts.itemis.cloud/repository/maven-mps/") }
    mavenCentral()
}

downloadJbr {
    jbrVersion = libs.versions.jbr.get()
}

// configurations
val mps: Configuration = configurations.create("mps")
val junit: Configuration = configurations.create("junit")
val mpsDependencies: Configuration = configurations.create("mpsDependencies")
// model checker runtime used by MpsCheck, which looks it up by this name
val modelcheckBackend: Configuration = configurations.create("modelcheckBackend")

// dependencies
dependencies {
    junit(libs.ant.junit)
    mps(libs.mps)
    mpsDependencies(libs.mps.mbeddr)
    mpsDependencies(libs.mps.mbeddr.platform)
    mpsDependencies(libs.mps.extensions)
    mpsDependencies(libs.mps.iets3.opensource)
    modelcheckBackend(libs.mps.modelcheckBackend)
}

// Extraction is skipped when the target already holds the same artifacts, e.g. restored from the CI cache.
// Gradle's own up-to-date check cannot detect that, as its task history (.gradle/) is not part of that cache.
fun Task.skipIfExtracted(targetDir: File, id: String) {
    val marker = targetDir.resolve(".extracted")
    onlyIf("$targetDir does not contain $id yet") { !(marker.isFile && marker.readText() == id) }
    doLast { marker.writeText(id) }
}

fun Configuration.fingerprint() = dependencies.joinToString(",") { "${it.group}:${it.name}:${it.version}" }

tasks.extractJbr {
    skipIfExtracted(file("$buildPath/jbrDownload"), "jbr:${libs.versions.jbr.get()}")
}

val extractMps = tasks.register<Copy>("extractMps") {
    dependsOn(tasks.extractJbr)
    from({ mps.resolve().map { zipTree(it) } })
    into(mpsGenericPath)
    skipIfExtracted(mpsGenericPath.toFile(), mps.fingerprint())
}

val extractMpsDependencies = tasks.register<Copy>("extractMpsDependencies") {
    dependsOn(extractMps)
    from({ mpsDependencies.resolve().map { zipTree(it) } })
    into(dependencyInstallPath)
    skipIfExtracted(dependencyInstallPath.toFile(), mpsDependencies.fingerprint())
}

val setup = tasks.register("setup") {
    group = "Setup"
    description = "Download and extract MPS and the all MPS dependencies."

    dependsOn(extractMpsDependencies)

    // ant scripts run against the MPS extracted above (version from libs.versions.toml)
    ext["itemis.mps.gradle.ant.defaultScriptArgs"] = listOf("-Dmps_home=$mpsGenericPath")
    ext["itemis.mps.gradle.ant.defaultScriptClasspath"] = project.configurations["junit"]
}

// 'static' MPS build solution to build the actual build and test XMLs
// -PprebuiltBuildScripts: use the generated ant scripts already present (CI generates them once and shares them)
val prebuiltBuildScripts = providers.gradleProperty("prebuiltBuildScripts")
val buildScripts = tasks.register<BuildLanguages>("buildScripts") {
    group = "build"
    description = "Build the buildAll.xml ANT configuration needed to build the MPS project."

    dependsOn(setup)
    script = "$projectDir/buildAll.xml"
    onlyIf("ant scripts are not prebuilt (-PprebuiltBuildScripts)") { !prebuiltBuildScripts.isPresent }
}

val buildLanguages = tasks.register<BuildLanguages>("buildLanguages") {
    dependsOn(buildScripts)
    group = "build"
    description = "Build all languages in the MPS project via build.xml."
    script = "build.xml"
}

// Tests are run headless via ant scripts generated from the build model: interpreter tests by iets3's
// interpreterExecutor, generated tests by MPS' module tests (JUnit). Each task aggregates the JUnit results
// (resultFiles) into <resultsDir>/html and fails on test failures.
// Without antTargets, TestLanguages' defaults (clean, generate, assemble, check) apply. 'clean' drops the MPS
// system dir of the previous run: its cached file contents would otherwise hide model changes made since then
// (headless MPS does not refresh them on startup).
fun TestLanguages.runMpsTests(
    antScript: String,
    resultsDir: Provider<Directory>,
    resultFiles: String = "**/InterpreterTestSuite*.xml",
    antTargets: List<String>? = null,
) {
    group = "verification"
    script = antScript
    antTargets?.let { targets(*it.toTypedArray()) }
    doFirst { delete(resultsDir) }
    doLast {
        val results = resultsDir.get().asFile
        ant.withGroovyBuilder {
            "taskdef"(
                "name" to "junitMpsReport",
                "classname" to "org.apache.tools.ant.taskdefs.optional.junit.XMLResultAggregator",
                "classpath" to junit.asPath
            )
            "junitMpsReport"("toDir" to results) {
                "fileset"("dir" to results, "includes" to resultFiles)
                "report"("format" to "frames", "todir" to "$results/html")
            }
        }
        val summary = results.resolve("TESTS-TestSuites.xml").readText()
        // The runners only log (and run nothing) when they are misconfigured, e.g. when no output folder
        // reaches them - so an empty report must fail, too.
        if (!summary.contains("<testsuite ")) {
            throw GradleException("No test results in $results - check the ant output for runner errors")
        }
        if (Regex("""<testsuite [^>]*(failures|errors)="[1-9]""").containsMatchIn(summary)) {
            throw GradleException("Tests failed, see file://$results/html/index.html")
        }
        logger.lifecycle("Test report: file://$results/html/index.html")
    }
}

// the interpreter test scripts have no 'check' target; their 'build' runs the interpreter
val interpreterTestTargets = listOf("clean", "generate", "build")

// Case 1 - no build needed: the tests in HeadlessInterpreterTest.tests are plain user models written
// with published iets3 languages only. They are loaded straight from their source folder and
// interpreted; nothing of this project is generated or compiled. Only the ant script itself is
// generated from the build model (buildScripts), as it is not checked in.
val runInterpretedTests = tasks.register<TestLanguages>("runInterpretedTests") {
    dependsOn(buildScripts)
    description = "Interpret the user-model tests (HeadlessInterpreterTest.tests) without building anything."
    runMpsTests(
        "run-interpreted-no-build-tests.xml", layout.buildDirectory.dir("test-results/interpreted-no-build"),
        antTargets = interpreterTestTargets,
    )
}

// Case 2 - own language: the tests in HeadlessInterpreterTest.languageTests use the project's own
// language (HeadlessInterpreterTest) and its interpreter. These must be compiled, so the language
// plugin is built first and loaded from build/artifacts/headless-interpreter-sample.
val runInterpretedLanguageTests = tasks.register<TestLanguages>("runInterpretedLanguageTests") {
    dependsOn(buildLanguages)
    description = "Build the project's language and interpret the tests that use it (HeadlessInterpreterTest.languageTests)."
    runMpsTests(
        "run-interpreted-lang-build-tests.xml", layout.buildDirectory.dir("test-results/interpreted-lang-build"),
        antTargets = interpreterTestTargets,
    )
}

// Model checking of the whole MPS project. The project's own language must be compiled (classes_gen) for its
// models to be checked, so the languages are built first. The dependencies are loaded via the project library
// (mpsModules/.mps/libraries.xml -> build/dependencies).
val checkModels = tasks.register<MpsCheck>("checkModels") {
    dependsOn(buildLanguages)
    description = "Run the MPS model checker on all modules of the project."
    // same JBR as the ant tasks (downloadJbr); JavaExec rejects an executable that differs from its javaLauncher
    javaLauncher.set(tasks.downloadJbr.flatMap { it.javaLauncher })
    mpsHome.set(layout.dir(provider { mpsGenericPath.toFile() }))
    projectLocation.set(layout.projectDirectory.dir("mpsModules"))
    pluginRoots.add(mpsHome.dir("plugins"))
    junitFile.set(layout.buildDirectory.file("test-results/checkmodels/TEST-checkModels.xml"))
    // one test case per message
    junitFormat.set("message")
    maxHeapSize = "4G"
}

tasks.check {
    dependsOn(runInterpretedTests, runInterpretedLanguageTests, checkModels)
}

// Demo of a failing run - not part of 'check'. HeadlessInterpreterTest.failingTests contains a test that fails
// on purpose; the task fails and the report shows the failure with its node URL and the nodeRef properties.
tasks.register<TestLanguages>("runFailingInterpretedTests") {
    dependsOn(buildScripts)
    description = "Interpret HeadlessInterpreterTest.failingTests, which contains a broken test - this task is expected to fail."
    runMpsTests(
        "run-interpreted-failing-tests.xml", layout.buildDirectory.dir("test-results/interpreted-failing"),
        antTargets = interpreterTestTargets,
    )
}

// Case 3 - generated tests: the tests in HeadlessInterpreterTest.generatedTests (published iets3 languages only)
// are generated to JUnit test classes, compiled and run in a headless MPS by MPS' module tests.
val generatedTestResults = "**/TEST-*.xml"

val runGeneratedTests = tasks.register<TestLanguages>("runGeneratedTests") {
    dependsOn(buildScripts)
    description = "Generate, compile and run the tests in HeadlessInterpreterTest.generatedTests as JUnit tests."
    runMpsTests(
        "run-generated-tests.xml", layout.buildDirectory.dir("test-results/generated"),
        generatedTestResults,
    )
}

tasks.check {
    dependsOn(runGeneratedTests)
}

// Demo of a failing generated run - not part of 'check'. HeadlessInterpreterTest.generatedFailingTests contains
// a passing and a broken test; the task is expected to fail.
tasks.register<TestLanguages>("runFailingGeneratedTests") {
    dependsOn(buildScripts)
    description = "Generate and run HeadlessInterpreterTest.generatedFailingTests, which contains a broken test - this task is expected to fail."
    runMpsTests(
        "run-generated-failing-tests.xml", layout.buildDirectory.dir("test-results/generated-failing"),
        generatedTestResults,
    )
}

tasks.assemble {
    dependsOn(buildLanguages)
}

// all ant based tasks run with the downloaded JBR
tasks.withType<RunAntScript>().configureEach { executable = tasks.downloadJbr.get().javaExecutable }

// so that no task has to be specified when running gradle
defaultTasks(buildLanguages.name)
