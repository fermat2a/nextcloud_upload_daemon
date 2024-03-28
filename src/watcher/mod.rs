use notify::{Event, RecommendedWatcher, RecursiveMode, Watcher};
use std::path::Path;

fn event_dispatcher(event: Event) {
    if let notify::event::EventKind::Access(notify::event::AccessKind::Close(
        notify::event::AccessMode::Write,
    )) = event.kind
    {
        println!("Close of write file event: {:?}", event);
    }
}

pub fn create_watcher(
    directory_path: &str,
) -> Result<RecommendedWatcher, Box<dyn std::error::Error>> {
    // Automatically select the best implementation for your platform.
    let mut dir_watcher = notify::recommended_watcher(|res| match res {
        Ok(event) => event_dispatcher(event),
        Err(e) => println!("watch error: {:?}", e),
    })?;

    // Add a path to be watched. All files and directories at that path and
    // below will be monitored for changes.
    dir_watcher.watch(Path::new(directory_path), RecursiveMode::Recursive)?;

    Ok(dir_watcher)
}
