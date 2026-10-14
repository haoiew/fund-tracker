import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python") version "17.1.0"
}

android {
    namespace = "com.fundtracker.backend"
    compileSdk = 37
    defaultConfig {
        minSdk = 24
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
        consumerProguardFiles("consumer-rules.pro")
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
}
kotlin { compilerOptions { jvmTarget = JvmTarget.JVM_1_8 } }

// Copy application code only: never package the desktop .env, database or holdings.
val backendSources = layout.buildDirectory.dir("generated/backend")
val syncBackendSources by tasks.registering(Sync::class) {
    from(file("../../../../../backend")) { include("app/**"); exclude("**/__pycache__/**", "**/*.pyc") }
    into(backendSources)
}
chaquopy {
    defaultConfig {
        version = "3.11"
        System.getenv("FUND_TRACKER_BUILD_PYTHON")?.let { buildPython(it) }
        pip {
            options("--find-links", file("wheels").absolutePath)
            install("-r", file("requirements-android.txt").absolutePath)
        }
    }
    sourceSets { getByName("main") { srcDir(backendSources) } }
}
tasks.configureEach {
    if (name.contains("Python")) dependsOn(syncBackendSources)
}
dependencies { implementation(project(":tauri-android")) }
