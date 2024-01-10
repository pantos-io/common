# Common code for Pantos off-chain components

## 1. Introduction

### 1.1 Overview

Welcome to the documentation for Pantos Common. This repository is a centralized hub for storing shared code components used across multiple projects within our organization.

The primary purpose of the Common Repository is to promote code reusability, streamline collaboration, and maintain consistency across various projects. Centralizing shared code aims to enhance efficiency and reduce redundancy in our development processes.

### 1.2 Features

The Pantos Common project currently offers the following functionalities:

#### Signing module
The **signer.py** module is used for signing and verifying signatures. The private key must be on the curve Ed25519 or Ed448 and encrypted in a PEM file.

#### Service nodes module
The **servicenodes.py** module is used for communicating with Pantos service nodes. It can be used for querying the bids, sending transfers, and requesting the transfer status.

#### Blockchain utility modules
The blockchain utility modules extract common blockchain functionalities used across projects. Such functionalities include sending transactions or calling the blockchain nodes for read-only data.

The blockchain utility modules can be found in the **blockchains** package. There is a Python module for each Pantos-supported blockchain.

## 2. Installation

### 2.1  Prerequisites

Please make sure that your environment meets the following requirements:

#### Python Version

The Pantos Client CLI requires **Python 3.10**. Ensure that you have the correct Python version installed before the installation steps. You can download the latest version of Python from the official [Python website](https://www.python.org/downloads/).

#### Library Versions

The Pantos Common project has been tested with the library versions in **requirements.txt**.

### 2.2  Installation Steps

#### Virtual environment

Create a virtual environment from the repository's root directory:

```bash
$ python -m venv .venv
```

Activate the virtual environment:

```bash
$ source .venv/bin/activate
```

Install the required packages:
```bash
$ python -m pip install -r requirements.txt
```

## 3. Usage

The Pantos Common project should be used as a utility library, for example as a submodule in an upstream project. After those steps, the modules can be imported directly from the Common library.

### 3.1 Examples

https://github.com/pantos-io/client-library/blob/main/pantos/client/library/blockchains/base.py

## 4. Contributing

At the moment, contributing to this project is not available. 
