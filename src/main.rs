use log::{info, debug};

pub mod configuration;

fn main() {
    env_logger::init();
    info!("starting up");
    let scrape_config: configuration::Configuration = configuration::load_configuration("login_credentials.yaml");
    debug!("got Configuration: {:?}", scrape_config);
}
