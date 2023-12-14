use serde::{Deserialize, Serialize};
use serde_yaml::{self};
use log::debug;

#[derive(Debug, Serialize, Deserialize)]
pub struct Configuration {
    address: String,
    username: String,
    password: String,
}

pub fn load_configuration(ref filepath : &str) -> Configuration {
    debug!("loading configuration from {}", filepath);
    let f = std::fs::File::open("login_credentials.yaml").expect("Could not open configuration file");
    let scrape_config: Configuration = serde_yaml::from_reader(f).expect("Could not read values from configuration file");
    debug!("Configuration: {:?}", scrape_config);
    scrape_config
}