const COMMANDS: &[&str] = &["start_backend", "save_file"];

fn main() {
  tauri_plugin::Builder::new(COMMANDS)
    .android_path("android")
    .build();
}
