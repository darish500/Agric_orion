from setuptools import find_packages, setup

package_name = 'agric_orion'
import os

from glob import glob

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
    ('share/ament_index/resource_index/packages', ['resource/agric_orion']),
    ('share/agric_orion', ['package.xml']),
    (os.path.join('share', 'agric_orion', 'urdf'), glob('urdf/*.urdf')),
    (os.path.join('share', 'agric_orion', 'launch'), glob('launch/*.launch.py')),
    (os.path.join('share', 'agric_orion' , 'urdf'), glob('urdf/*.urdf') + glob('urdf/*.xacro')),
    (os.path.join('share', 'agric_orion','config'), glob('config/*.yaml')),
    (os.path.join('share' , 'agric_orion', 'worlds'), glob('worlds/*.sdf')),
    (os.path.join('share' , 'agric_orion' , 'maps') , glob("maps/*.pgm") + glob('maps/*.yaml')),

    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='inspiredkhalid',
    maintainer_email='rasakkhalid145@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'world_state_node = agric_orion.world_state_node:main',
            'test_follow_path = agric_orion.test_follow_path:main',
            'nav2_eval_node = agric_orion.nav2_eval_node:main', 
            'agent_bridge_node = agric_orion.agent_bridge_node:main',
            'mission_context_node = agric_orion.mission_context_node:main'
        ],
    },
)
