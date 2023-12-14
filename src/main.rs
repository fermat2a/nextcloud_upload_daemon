use log::{info, debug};

pub mod configuration;

fn main() {
    env_logger::init();
    info!("starting up");
    let scrape_config = configuration::load_configuration("login_credentials.yaml").expect("Could no load config file.");
    debug!("got Configuration: {:?}", scrape_config);
}
