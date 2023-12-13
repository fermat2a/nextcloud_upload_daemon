use serde::{Deserialize, Serialize};
use serde_yaml::{self};
use log::{info, debug};

#[derive(Debug, Serialize, Deserialize)]
struct Login {
    address: String,
    username: String,
    password: String,
}

fn main() {
    env_logger::init();
    info!("starting up");
    let f = std::fs::File::open("login_credentials.yaml").expect("Could not open file.");
    let scrape_config: Login = serde_yaml::from_reader(f).expect("Could not read values.");
    debug!("Configuration: {:?}", scrape_config);
}
