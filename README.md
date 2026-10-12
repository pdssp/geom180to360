# geom180to360

[![image](https://img.shields.io/badge/Maintained%3F-yes-green.svg)]()

![image]()

Conversion tool of geometries from longitudes [-180, 180] to [0, 360]

## Stable release

To install geom180to360, run this command in your
terminal:

``` console
$ pip install git+https://gitlab.cnes.fr/pdssp/common/geom180to360.git
```

This is the preferred method to install geom180to360,
as it will always install the most recent stable release.

If you don\'t have [pip](https://pip.pypa.io) installed, this [Python
installation
guide](http://docs.python-guide.org/en/latest/starting/installation/)
can guide you through the process.

## Installing UV

To manage the dependencies of geom180to360, we use
[UV](<https://docs.astral.sh/uv/>). If you don\'t have UV
installed, follow these steps:

1.  **Install UV**:

    > ``` shell
    > $ curl -LsSf https://astral.sh/uv/install.sh | sh
    > ```

2.  **Verify the installation**:

    > ``` console
    > $ uv --version
    > ```

Please note that this project has been tested with UV version 0.9.15.

## From sources

The sources for geom180to360 can be downloaded from
the [Gitlab repo]().

You can either clone the public repository:

``` console
$ git clone https://gitlab.cnes.fr/pdssp/common/geom180to360.git
```

Or download the
[tarball]():

``` console
$ curl -OJL https://gitlab.cnes.fr/pdssp/common/geom180to360/tarball/main
```

Once you have a copy of the source, you can install it with:

``` console
$ make  # install
```

## Development

``` console
$ git clone https://gitlab.cnes.fr/pdssp/common/geom180to360.git
$ cd geom180to360
$ make prepare-dev
$ source .venv/bin/activate
$ make install-dev
```

To get more information about the preconfigured tasks:

``` console
$ make help
```

## Usage

To use geom180to360 in a project:

``` shell
import geom180to360
```

If the Docker image has been created, use the Docker image with the
following command line.

``` console
$ docker run -u $(id -u):$(id -g) -v $(pwd):/app --rm --name geom180to360 pdssp/geom180to360
```

## Run tests

``` console
$make tests
```

## Documentation

The documentation is automatically deployed on
<https://pdssp.io.cnes.fr/>geom180to360 based on main branch

## Container

A container image is automatically built and published to CNES Artifactory.  
The image tag and publication registry depend on the CI pipeline: 

| CI Pipeline     | Container tag   | Publication registry           |
| --------------- | --------------- | ------------------------------ |
| Git commit      | Git branch name | development
| Git tag         | Git tag name    | production 

## Author

👤 **Jean-Christophe MALAPERT**

## 🤝 Contributing

Contributions, issues and feature requests are welcome!  
Feel free to check [issues page](https://gitlab.cnes.fr/pdssp/common/geom180to360/issues).  
You can also take a look at the [contributing guide](https://gitlab.cnes.fr/pdssp/common/geom180to360/blob/main/CONTRIBUTING.rst)

## 📝 License

This project is [Apache V2.0](https://gitlab.cnes.fr/pdssp/common/geom180to360/blob/main/LICENSE) licensed.
