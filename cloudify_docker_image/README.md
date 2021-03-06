# Installation
## Ubuntu:
1. First run `./install_ubuntu`
1. Logout and log back in.
1. `docker ps` should work now.

## Centos 7:
1. First run `./install_centos`
2. Logout and log back in.
3. `docker ps` should work now.

## OpenStack Known issues
### Containers don't have any network access
If the container doesn't have network access, run `./centos_mtu_fix`. This will change the docker bridge
mtu and use the gateway interface's mtu.

# Usage
- To create the base image, configure the constants and run
    ```
    bash make_base_image.sh
    ```

- To create the Cloudify Manager image (you have to first create the base image), configure the constants and run 
    ```
    bash make_cfy_manager_image.sh CFY_RPM_URL_with_cfy_manager_ install
    ``` 
  - Note that you'll need to set the environmental variables `DOCKER_ID_USER` and `DOCKER_ID_PASSWORD` variables with the Docker ID username and password respectively:
	  ```
	  export DOCKER_ID_USER="username"
	  export DOCKER_ID_PASSWORD="password"
	  ```
  - You can setup your own tags for the image by manipulating the array `IMAGE_TAGS`.
- Pull image from the repository (may require a `docker login`)
  ```
  # Might not be necessary - the recommended way (interactive)
  docker login
  # Fill in the Username and Password when prompted
  # Or run the following command, preferably with env vars
  docker login -u=$DOCKER_ID_USER -p=$DOCKER_ID_PASSWORD

  # Pull the image
  docker pull cloudifycosmo/REPO_NAME:TAG
  
  # Spin up the manager
  docker run --name ARBITRARY_CONTAINER_NAME -d --restart unless-stopped \
  -v /sys/fs/cgroup:/sys/fs/cgroup:ro -p 8080:8080 -p 1025:22 -p 80:80 \
  -p 5671:5671 -p 5672:5672 -p 15672:15672 -p 9200:9200 \
  -p 5432:5432 -p 8086:8086 -p 999:999 --tmpfs /run --tmpfs /run/lock --security-opt \
  seccomp:unconfined --cap-add SYS_ADMIN cloudifycosmo/REPO_NAME:TAG
  
  # To connect to the manager via the Cloudify CLI, print the container's IP
  docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' CONTAINER_NAME
  ```
  _Note: port 1025 was chosen from a list of unused ports in most Linux machines, if 
  this port is not available on your host, please choose a different one and replace `-p 
  1025:22` with your own port number._
- Load the image locally with
  ```
  docker load < IMAGE_TAR_FILE
  ```
  - Run a manager container from that image with
    ```
    docker run --name ARBITRARY_CONTAINER_NAME -d --restart unless-stopped \
    -v /sys/fs/cgroup:/sys/fs/cgroup:ro -p 8080:8080 -p 1025:22 -p 80:80 \
    -p 5671:5671 -p 5672:5672 -p 15672:15672 -p 9200:9200 \
    -p 5432:5432 -p 8086:8086 -p 999:999 --tmpfs /run --tmpfs /run/lock --security-opt \
    seccomp:unconfined --cap-add SYS_ADMIN IMAGE_NAME
    ```
    _Note: port 1025 was chosen from a list of unused ports in most Linux machines, if 
    this port is not available on your host, please choose a different one and replace `-p 
    1025:22` with your own port number._
- Connecting with `ssh` directly to the container
  1. Run the container with one of the commands here above.
  1. Generate an `ssh` key with `ssh-keygen` and copy the contents of the public key.
  1. Connect to the container from the host via `docker exec -it CONTAINER_NAME bash`.
  1. `cd ~/.ssh`
  1. `vi authorized_keys` paste the public key contents you have copied in previous steps 
  and save.
  1. Save the changes to the container `docker commit -m "Setup direct ssh" CONTAINER_NAME
   SOME_IMAGE_NAME`.
  1. Now you can connect directly to the container using the regular `ssh -i KEY_PATH 
  root@HOST_IP -p 1025` or whatever port you've setup instead of `1025`. 
