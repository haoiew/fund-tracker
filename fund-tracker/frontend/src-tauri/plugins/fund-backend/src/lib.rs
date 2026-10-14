use tauri::{plugin::{Builder, TauriPlugin}, Runtime};
#[cfg(target_os = "android")]
use tauri::{plugin::PluginHandle, Manager};

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection { api_base_url: String, access_token: String }

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct SaveFile { filename: String, mime_type: String, content: String }

#[derive(serde::Serialize, serde::Deserialize)]
struct SaveResult { saved: bool }

#[cfg(target_os = "android")]
struct Backend<R: Runtime>(PluginHandle<R>);

#[tauri::command]
async fn start_backend<R: Runtime>(app: tauri::AppHandle<R>) -> Result<BackendConnection, String> {
    #[cfg(target_os = "android")]
    {
        tauri::async_runtime::spawn_blocking(move || {
            app.state::<Backend<R>>().0.run_mobile_plugin("startBackend", ())
                .map_err(|error| error.to_string())
        }).await.map_err(|error| error.to_string())?
    }
    #[cfg(not(target_os = "android"))]
    {
        let _ = app;
        Err("The embedded backend is available on Android only".into())
    }
}

#[tauri::command]
async fn save_file<R: Runtime>(app: tauri::AppHandle<R>, file: SaveFile) -> Result<SaveResult, String> {
    #[cfg(target_os = "android")]
    {
        tauri::async_runtime::spawn_blocking(move || {
            app.state::<Backend<R>>().0.run_mobile_plugin("saveFile", file)
                .map_err(|error| error.to_string())
        }).await.map_err(|error| error.to_string())?
    }
    #[cfg(not(target_os = "android"))]
    {
        let _ = (app, file);
        Err("The Android document picker is not available in this shell".into())
    }
}

pub fn init<R: Runtime>() -> TauriPlugin<R> {
    Builder::new("fund-backend")
        .invoke_handler(tauri::generate_handler![start_backend, save_file])
        .setup(|app, api| {
            #[cfg(target_os = "android")]
            app.manage(Backend(api.register_android_plugin("com.fundtracker.backend", "FundBackendPlugin")?));
            #[cfg(not(target_os = "android"))]
            let _ = (app, api);
            Ok(())
        })
        .build()
}
