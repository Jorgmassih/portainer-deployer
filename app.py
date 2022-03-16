import argparse
import configparser
import sys
import os
import requests
from urllib3.exceptions import InsecureRequestWarning
from utils.utils import *


class PortainerAPIConsumer:
    
    def __init__(self, path_to_config: str):
        PATH_TO_CONFIG = path_to_config

        # Load config
        config = configparser.ConfigParser()
        config.read(PATH_TO_CONFIG)
        self._portainer_config = config['PORTAINER']

        # Set non-ssl connection
        if not self._portainer_config.getboolean('SSL') and self._portainer_config['URL'].split('://')[0] == 'https':
            # Suppress only the single warning from urllib3 needed.
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

        # Set portainer connection parameters
        self.__portainer_connection_str = f"{self._portainer_config['URL']}:{self._portainer_config['PORT']}" 
        self.__connection_headers = {'X-API-Key': self._portainer_config['TOKEN']}


    def get_stack(self, name:str=None, stack_id:int=None):
        """_summary_: Get a stack from portainer

        Args:
            name (str, optional): Name of the stack in Portainer. Defaults to None.
            stack_id (int, optional): Id of the stack in Portainer. Defaults to None.
        """
        r = requests.get(
            f"{self.__portainer_connection_str}/api/stacks", 
            headers=self.__connection_headers,
            verify=False
        )
        data = r.json()

        spacing_str = '{0:<5} {1:<12} {2:<30} {3:30} {4:<30}'
        print(spacing_str.format('Id', 'Endpoint Id', 'Name', 'Creation', 'Last Updated'))

        data = format_stack_list(data)
        
        # Return all stacks if name and id aren't set
        if not name and not stack_id:
            for stack in data:
                print(spacing_str.format(*stack))
        
        # Return a specific stack given by the name
        elif name and not stack_id:
            for stack in data:
                if stack[2] == name:
                    print(spacing_str.format(*stack))
        
        # Return a specific stack given by the stack id
        else:
            for stack in data:
                if stack[0] == stack_id:
                    print(spacing_str.format(*stack))


    def post_stack_from_str(self, stack: str, endpoint_id: int, name: str = generate_random_hash()):
       #TODO: Implement
       pass


    def post_stack_from_file(self, path: str, endpoint_id: int, name: str = generate_random_hash()):
        # Open file
        with open(path, 'r') as f:
            form_data = {
                'Name': name
            }
            
            params = {
                "type": 2,
                "endpointId": endpoint_id,
                "method": "file"
            }
            
            r = requests.post(self.__portainer_connection_str + '/api/stacks',
                 data=form_data, 
                 params=params,
                 files={'file': f},
                 headers=self.__connection_headers, 
                 verify=False
            )
            print(r.status_code, r.text)
    

    def update_stack(self, stack_id: str, stack: str):
        #TODO: Implement
        pass


class PortainerDeployer:
    """Manage Portainer's Stacks usgin its API.
    """
    def __init__(self):
        """Initialize the PortainerDeployer class and runs the main function.
        """        
        # Load .env file
        env_file = configparser.ConfigParser()
        env_file.read('.env')
        PATH_TO_CONFIG = env_file['CONFIG']['PATH_TO_CONFIG']


        # Set API consummer object
        self.api_consumer = PortainerAPIConsumer(path_to_config=PATH_TO_CONFIG)
        
        # Set arguments
        self._main_parser, self._get_parser, self._deploy_parser, = self.__parser()
        self._parser_args = self._main_parser.parse_args()

        
        subparsers = {'get': self._get_parser, 'deploy': self._deploy_parser}

        # Run the default function
        selected_subparser = self._parser_args.subparser_name
        if selected_subparser:
            if len(sys.argv) == 2:
                subparsers[selected_subparser].print_help()
                sys.exit(1)
            self._parser_args.func(self._parser_args, subparsers[selected_subparser])


    def __parser(self) -> argparse.ArgumentParser:
        """Parse arguments from the command line.

        Returns:
            argparse.ArgumentParser: Parser Object.
        """        
        
        parser = argparse.ArgumentParser(
            description='Deploy stacks to portainer',
            prog='portainerDeployer'
        )
        
        subparsers = parser.add_subparsers(help='Sub-commands for actions', dest='subparser_name')

        # Create the parser for the "get" command
        parser_get = subparsers.add_parser('get', 
            help='Help for action Get', 
            description='Get a stack info from portainer.'
        )
        
        # Mutually exclusive arguments for --name and --id
        mutually_exclusive_name_id = parser_get.add_mutually_exclusive_group()

        mutually_exclusive_name_id.add_argument('--id',
            action='store',
            help="Id for the stack when set action to 'get'",          
            type=int
        )

        mutually_exclusive_name_id.add_argument('--name',
            '-n',
            action='store',
            help="Name of the stack to look for",   
            type=str
        )


        mutually_exclusive_name_id.add_argument('--all',
            '-a',
            action='store_true',
            help="Gets all stacks in portainer",   
        )

        parser_get.set_defaults(func=self.__get_sub_command)


        # create the parser for the "deploy" command
        parser_deploy = subparsers.add_parser('deploy', help='Help for action Deploy')

        mutually_exclusive_stack_path = parser_deploy.add_mutually_exclusive_group()

        mutually_exclusive_stack_path.add_argument('--stack',
            type=str, 
            help="Docker Compose string for the satack",
            nargs='?',
            default=(None if sys.stdin.isatty() else sys.stdin))

        
        mutually_exclusive_stack_path.add_argument('--path',
            '-p',
            action='store',
            type=str,
            help='The path to Docker Compose file for the stack',
            required=False,
            default=None)

        
        parser_deploy.add_argument('--update-keys', 
            '-u',
            action='extend', 
            type=str,
            nargs='*',
            help='Modify the stack file/string by passing a list of key=value pairs, where the key is in dot notation. i.e. a.b.c=value1 d=value2',
        )


        parser_deploy.add_argument('--endpoint', 
            '-e',
            action='store',
            type=int,
            help='Endponint Id in Portainer'
        )


        parser_deploy.set_defaults(func=self.__deploy_sub_command)

        parser.add_argument('--version', action='version', version='%(prog)s 0.0.1 (Alpha)')

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)
        
        return parser, parser_get, parser_deploy


    def __get_sub_command(self , args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
        if args.all:
            self.api_consumer.get_stack()
        else:
            self.api_consumer.get_stack(name=args.name, stack_id=args.id)


    def __deploy_sub_command(self, args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
        if args.stack:
            if args.update_keys:
                parser.error('You can not use "--update-keys" argument with "--stack" argument. It is only available for "--path" argument.')
            self.api_consumer.post_stack_from_str(stack=args.stack, endpoint_id=args.endpoint)
        
        elif args.path:
            if not os.path.isfile(args.path):
                parser.error('The specified file does not exist.')

            if args.update_keys:
                for pair in args.update_keys:
                    if validate_key_value(pair=pair):

                        keys, new_value = pair.split('=')
                        edited = edit_yml_file(path=args.path, key_group=keys, new_value=new_value)
                        if edited:
                            parser.error(edited)

            self.api_consumer.post_stack_from_file(path=args.path, endpoint_id=args.endpoint)




if __name__ == '__main__':
    PortainerDeployer()