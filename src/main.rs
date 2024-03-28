use log::{debug, info};
use std::{thread, time};
//use notify::RecommendedWatcher;

pub mod configuration;
pub mod watcher;

fn main() {
    env_logger::init();
    info!("starting up");
    let scrape_config = configuration::load_configuration("login_credentials.yaml")
        .expect("Could no load config file.");
    debug!("got Configuration: {:?}", scrape_config);
    let _directory_watcher = match watcher::create_watcher(scrape_config.local_path.as_str()) {
        Err(_) => panic!("Could not watch"),
        Ok(watcher) => watcher,
    };
    thread::sleep(time::Duration::from_secs(60));
}
