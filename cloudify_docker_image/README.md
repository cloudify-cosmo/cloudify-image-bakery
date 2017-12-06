# General Usage
 - _Note: tested on a Ubuntu 16.04.3 LTS (Xenial Xerus) host._
 
## Perquisites
###Ubuntu:
`sudo apt install -y docker.io`.

### Follow through these instructions to setup everything for the `dockerd` daemon
1. `sudo usermod -aG docker <CURRENT_USERNAME>`.
1. logout & log back in.
1. check that `docker ps` command works.

## Usage
- To create the base image, configure the constants and run
    ```
    bash make_base_image.sh
    ```

- To create the Cloudify Manager image (you have to first create the base image), configure the constants and run 
    ```
    bash make_cfy_manager_image.sh <CFY RPM with cfy_manager install>
    ``` 
  - Note that you'll need to set the environmental variables `DOCKER_ID_USER` and `DOCKER_ID_PASSWORD` variables with the Docker ID username and password respectively:
	  ```
	  export DOCKER_ID_USER="username"
	  export DOCKER_ID_PASSWORD="password"
	  ```
  - You can setup your own tags for the image by manipulating the array `IMAGE_TAGS`.
- Load the image locally with
  ```
  docker load < <IMAGE_TAR_FILE>
  ```
  - Run a manager container from that image with
    ```
    docker run --name <ARBITRARY_CONTAINER_NAME> -d -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN <IMAGE_NAME>
    ```
