import os

import setuptools  # type: ignore

setuptools.setup(
    name='pantos-common', version=os.getenv('PANTOS_COMMON_VERSION', '0.0.0'),
    description='Common code for the Pantos off-chain components',
    packages=setuptools.find_packages(),
    package_data={'pantos.common.blockchains.contracts': ['*.abi']},
    install_requires=[
        'celery==5.3.1', 'Cerberus==1.3.4', 'Flask-RESTful==0.3.10',
        'JSON-log-formatter==0.5.2', 'PyYAML==6.0.1', 'requests==2.31.0',
        'web3==6.5.0', 'pyaml-env==1.2.1', 'python-dotenv==1.0.1',
        'hexbytes==0.3.1'
    ])
