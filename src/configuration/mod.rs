use log::debug;
use serde::{Deserialize, Serialize};
use serde_yaml::{self};

#[derive(Debug, Serialize, Deserialize)]
pub struct Configuration {
    address: String,
    username: String,
    password: String,
}

pub fn load_configuration(filepath: &str) -> Result<Configuration, Box<dyn std::error::Error>> {
    debug!("loading configuration from {}", filepath);
    let f = std::fs::File::open(filepath)?;
    serde_yaml::from_reader(f).map_err(|err| Box::new(err) as Box<dyn std::error::Error>)
}

#[cfg(test)]
mod tests {

    use super::*;

    #[test]
    fn load_configuration_success() {
        let scrape_config_result = load_configuration("login_credentials.yaml");
        assert!(
            scrape_config_result.is_ok(),
            "Error loading config file login_credentials.yaml"
        );
        let scrape_config = scrape_config_result.expect("Here should be dragons...");
        assert_eq!(
            scrape_config.address,
            "https://www.some_nextcloud_server.de"
        );
        assert_eq!(scrape_config.username, "IhrBenutzername");
        assert_eq!(scrape_config.password, "IhrPasswort");
    }

    #[test]
    fn load_configuration_failed_no_file() {
        let scrape_config_result = load_configuration("BAD_FILENAME.BLABLABLA");
        assert!(
            scrape_config_result.is_err(),
            "Found valid file with name BAD_FILENAME.BLABLABLA?!?!?"
        );
    }

    #[test]
    fn load_configuration_failed_invalid_file() {
        let scrape_config_result = load_configuration("README.md");
        assert!(
            scrape_config_result.is_err(),
            "Found valid file with name README.md?!?!?"
        );
    }
}
