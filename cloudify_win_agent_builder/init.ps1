echo "### Set verbose output ###"
$VerbosePreference="Continue"
$ErrorActionPreference="stop"
echo "### Set security protocol to TLS ###"
[Net.ServicePointManager]::SecurityProtocol = "tls12, tls11, tls"


function get_package ($package_url){
    $url = $package_url
    $file_name = Split-Path $url -leaf
    $file_ext = [IO.Path]::GetExtension($file_name)

    echo "### Download package from $url... ###"
    Invoke-WebRequest -Uri $url -OutFile $file_name
    echo "### installing $file_name... ###"
    if ($file_ext -eq '.msi'){
        Start-Process -FilePath "msiexec" -Wait -ArgumentList "/i $file_name /quiet /norestart ADDLOCAL=ALL"
    } else {
        Start-Process -FilePath ".\$file_name" -Wait -ArgumentList "/VERYSILENT"
    }

    ### Refresh path... ###
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}




echo "### Installing packages... ###"
get_package "https://www.python.org/ftp/python/2.7.15/python-2.7.15.msi"
get_package "https://github.com/git-for-windows/git/releases/download/v2.20.1.windows.1/Git-2.20.1-64-bit.exe"
get_package "https://download.microsoft.com/download/7/9/6/796EF2E4-801B-4FC4-AB28-B59FBF6D907B/VCForPython27.msi"
get_package "http://files.jrsoftware.org/is/5/isetup-5.5.5.exe"
get_package "https://s3.amazonaws.com/aws-cli/AWSCLI64PY3.msi"


echo "### Set Administrator password... ###"
net user Administrator $Env:password
