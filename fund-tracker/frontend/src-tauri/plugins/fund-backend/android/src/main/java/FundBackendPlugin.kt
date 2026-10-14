package com.fundtracker.backend

import android.app.Activity
import android.content.Intent
import android.util.Log
import androidx.activity.result.ActivityResult
import app.tauri.annotation.ActivityCallback
import app.tauri.annotation.Command
import app.tauri.annotation.InvokeArg
import app.tauri.annotation.TauriPlugin
import app.tauri.plugin.Invoke
import app.tauri.plugin.JSObject
import app.tauri.plugin.Plugin
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.util.concurrent.Executors

@InvokeArg
class SaveFileArgs {
    lateinit var filename: String
    lateinit var mimeType: String
    lateinit var content: String
}

@TauriPlugin
class FundBackendPlugin(private val activity: Activity) : Plugin(activity) {
    private val worker = Executors.newSingleThreadExecutor()

    @Command
    fun startBackend(invoke: Invoke) {
        worker.execute {
            try {
                if (!Python.isStarted()) Python.start(AndroidPlatform(activity.applicationContext))
                val connection = Python.getInstance().getModule("fund_tracker_android")
                    .callAttr("start", activity.filesDir.absolutePath).toString()
                val parsed = JSONObject(connection)
                val result = JSObject()
                result.put("apiBaseUrl", parsed.getString("apiBaseUrl"))
                result.put("accessToken", parsed.getString("accessToken"))
                invoke.resolve(result)
            } catch (error: Exception) {
                Log.e("FundTracker", "Embedded backend startup failed", error)
                invoke.reject("本地数据服务启动失败，请关闭应用后重试。" + (error.message ?: ""))
            }
        }
    }

    @Command
    fun saveFile(invoke: Invoke) {
        val args = invoke.parseArgs(SaveFileArgs::class.java)
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = args.mimeType
            putExtra(Intent.EXTRA_TITLE, args.filename)
        }
        startActivityForResult(invoke, intent, "fileCreated")
    }

    @ActivityCallback
    fun fileCreated(invoke: Invoke, result: ActivityResult) {
        val uri = result.data?.data
        if (result.resultCode != Activity.RESULT_OK || uri == null) {
            val response = JSObject()
            response.put("saved", false)
            invoke.resolve(response)
            return
        }
        val args = invoke.parseArgs(SaveFileArgs::class.java)
        worker.execute {
            try {
                val stream = activity.contentResolver.openOutputStream(uri, "wt")
                    ?: throw IllegalStateException("无法写入选中的文件")
                stream.use { it.write(args.content.toByteArray(Charsets.UTF_8)) }
                val response = JSObject()
                response.put("saved", true)
                invoke.resolve(response)
            } catch (error: Exception) {
                invoke.reject("保存文件失败：" + error.message)
            }
        }
    }
}
