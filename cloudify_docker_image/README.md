# General Usage
 - _Note: tested on a Ubuntu 16.04.3 LTS (Xenial Xerus) host._
 
## Perquisites
`sudo apt-get install -y docker`.

### Follow through these instructions to setup everything for the `dockerd` daemon
1. `sudo usermod -aG docker ubuntu`.
1. logout & log back in.
1. check that `docker ps` command works.

## Usage
- To create the base image 
    ```
    sh make_base_image.sh
    ```

- To create the Cloudify Manager image (you have to first create the base image) run 
    ```
    bash make_cfy_manager_image.sh <CFY RPM with cfy_manager install>
    ``` 
  - Note that you'll need to set the environmental variables `DOCKER_ID_USER` and `DOCKER_ID_PASSWORD` variables with the Docker ID username and password respectively:
	  ```
	  export DOCKER_ID_USER="username"
	  export DOCKER_ID_PASSWORD="password"
	  ```
  - You can setup your own tags for the image by adding more items to the array `IMAGE_TAGS`.