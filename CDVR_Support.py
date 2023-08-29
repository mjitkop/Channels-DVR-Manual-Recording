"""
Author: Gildas Lefur (a.k.a. "mjitkop" in the Channels DVR forums)

Description: This module provides generic definitions to interact with a 
             Channels DVR server. 

Disclaimer: this is an unofficial script that is NOT supported by the developers
            of Channels DVR.

Version History:
- 2023.06.24.2152: Started internal development.
- 2023.08.29.1630: First public release
"""

################################################################################
#                                                                              #
#                                   IMPORTS                                    #
#                                                                              #
################################################################################

import calendar, datetime, requests

from dateutil import tz

################################################################################
#                                                                              #
#                                  CONSTANTS                                   #
#                                                                              #
################################################################################

DEFAULT_PORT_NUMBER  = '8089'
LOOPBACK_ADDRESS     = '127.0.0.1'
VERSION              = '2023.08.29.1630'

################################################################################
#                                                                              #
#                                  FUNCTIONS                                   #
#                                                                              #
################################################################################

def convert_to_epoch_time(year, month, day, hour, minutes, seconds):
    local_timezone = get_local_timezone()

    dt = datetime.datetime(year, month, day, hour, minutes, seconds, tzinfo=local_timezone)
    epoch = calendar.timegm(dt.utctimetuple())

    return epoch

def convert_utc_time_to_local_time(utc_time):
    '''
    Takes UTC time in the format "2023-06-24T15:00Z" and convert it to the
    local time in the correct time zone.
    It will return this format: "Saturday, June 24, 2023 11:00:00 AM EDT".
    '''
    
    utc_format = "%Y-%m-%dT%H:%MZ"

    # Convert the UTC time string to a datetime object
    utc_dt = datetime.strptime(utc_time, utc_format)

    # Set the timezone for the datetime object to UTC
    utc_dt = utc_dt.replace(tzinfo=tz.tzutc())

    # Convert the UTC datetime object to the local timezone
    local_dt = utc_dt.astimezone(tz.tzlocal())

    # Format the local datetime object as a string
    local_time = local_dt.strftime('%A, %B %d, %Y %I:%M:%S %p %Z')

    return local_time

def get_local_timezone():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo

##############################################################################
#                                                                            #
#                             Class definitions                              #
#                                                                            #
##############################################################################

class ChannelsDVRServer:
    '''Attributes and methods to interact with a Channels DVR server.'''
    def __init__(self, ip_address=LOOPBACK_ADDRESS, port_number=DEFAULT_PORT_NUMBER):
        '''Initialize the server attributes.'''
        self.ip_address  = ip_address
        self.port_number = port_number
        self.url         = f'http://{self.ip_address}:{self.port_number}'

    def apply_label_to_program(self, program, label):
        '''Send a request to the server to apply the specified label to the given program.'''
        file_id = self.get_file_id(program)

        url_label = f'{self.url}/dvr/files/{file_id}/labels/{label}'

        requests.put(url_label)

    def check_pre_release(self):
        '''Send a request to the server to check for pre-release.'''
        url_check = f'{self.url}/updater/check/prerelease'

        response = requests.put(url_check)

        if response.status_code != 200:
            print(response.reason)
            print(response.text)

    def get_all_scheduled_recordings(self):
        '''Return all entries from the schedule in json format.'''
        url_jobs = f'{self.url}/dvr/jobs'
        
        return requests.get(url_jobs).json()
        
    def get_all_programs_from_library(self):
        '''Return all recordings and imports that are present in the library.'''
        url_files = f'{self.url}/dvr/files'
        
        return requests.get(url_files).json()
        
    def get_all_movies_from_library(self, library_files=None):
        '''Return a list of all movies that are in the library.'''
        movies = []
        
        if not library_files:
            library_files = self.get_all_programs_from_library()
        
        for f in library_files:
            categories = f['Airing'].get('Categories', None)
            
            if not categories:
                # Information not provided. Move on to the next file.
                continue
                
            if 'Movie' in categories:
                movies.append(f)
                
        return movies
        
    def get_all_series_from_library(self, library_files=None):
        '''Return a list of all programs from the library that are categorized as series.''' 
        series = []
        
        if not library_files:
            library_files = self.get_all_programs_from_library()
        
        for f in library_files:
            categories = f['Airing'].get('Categories', None)
            
            if not categories:
                # Information not provided. Move on to the next file.
                continue
                
            if 'Series' in f['Airing']['Categories']:
                series.append(f)
                
        return series
        
    def get_one_movie_from_library(self, movie_title, library_files=None):
        '''
        Check all programs in the library and return the program that is a movie
        with the desired title.
        '''
        movie = None
        
        all_movies = self.get_all_movies_from_library(library_files)
        
        for m in all_movies:
            library_movie_title = None
            
            raw_data = m['Airing'].get('Raw', None)
            if raw_data:
                library_movie_title = m['Airing']['Raw'].get('title', None)
            
            if library_movie_title == movie_title:
                movie = m
                break
                
        return movie
        
    def get_all_episodes_of_one_series_from_library(self, series_title, library_files=None):
        '''
        Check all programs in the library and return a list of all episodes of the series
        with the desired title.
        '''
        series_episodes = []
        
        all_series = self.get_all_series_from_library(library_files)
        
        for s in all_series:
            program_info = None
            
            raw_data = s['Airing'].get('Raw', None)
            
            if raw_data:
                program_info = s['Airing']['Raw'].get('program', None)
            
                if not program_info:
                    library_series_title = s['Airing']['Title']
                else:
                    library_series_title = program_info['title']
            else:
                library_series_title = s['Airing']['Title']
                
            if library_series_title == series_title:
                series_episodes.append(s)
                
        return series_episodes

    def get_channels(self):
        '''
        Return the list of all channels from all sources.

        The output will be a dictionary containing two sub-dictionaries:
        the first sub-dictionary will be indexed by channel numbers, and the
        second sub-dictionary will be indexed by channel names.
        {
            {<channel #>: <channel name>, ..., <channel #>: <channel name>},
            {<channel name>: <channel #>, ..., <channel name>: <channel #}
        }

        Each channel name will be a concatenation of the original channel name + the name of its source.
        For example, if the original channel name is "WABC" and the source is "TVE-DIRECTV":
        channel name = "WABC (TVE-DIRECTV)"
        '''
        all_channels = {}
        channels_indexed_by_numbers = {}
        channels_indexed_by_names   = {}

        url = f'http://{self.ip_address}:{self.port_number}/devices'

        devices = requests.get(url).json()

        for provider in devices:
            source = provider['DeviceID']

            for channel in provider['Channels']:
                number = int(channel['GuideNumber'])
                name   = f"{channel['GuideName']} ({source})"

                channels_indexed_by_numbers[number] = name
                channels_indexed_by_names[name] = number

        all_channels['numbers'] = channels_indexed_by_numbers
        all_channels['names']   = channels_indexed_by_names

        return all_channels

    def get_file_id(self, library_program):
        '''Return the ID of the given program from the library.'''
        return library_program['ID']

    def get_file_name(self, library_program):
        '''Return the full file name of the given program from the library.'''
        file_name = ''
        
        media_info = self.get_media_info(library_program)
        
        program_format = media_info.get('format', None)
        if program_format:
            file_name = media_info['format']['filename']
        else:
            print(media_info)
        
        return file_name
        
    def get_media_info(self, library_program):
        '''Return media information of the given library program.'''
        file_id = library_program['ID']
        
        return requests.get(f'{self.url}/dvr/files/{file_id}/mediainfo.json').json()

    def get_non_skipped_scheduled_recordings(self):
        '''Return all entries from the schedule that are not marked as skipped.'''
        url_jobs = f'{self.url}/dvr/jobs'
        
        return [job for job in requests.get(url_jobs).json() if not job['Skipped']]

    def get_one_episode_of_one_series_from_library(self, series_title, season_number, episode_number, library_files=None):
        '''Return the json data of the requested episode, if it is present in the library.'''
        episode = None
        
        all_episodes = self.get_all_episodes_of_one_series_from_library(series_title, library_files)
        
        for library_episode in all_episodes:
            ep_season_num = library_episode['Airing'].get('SeasonNumber', None)
            
            if ep_season_num == season_number:
                ep_num = library_episode['Airing'].get('EpisodeNumber', None)
                
                if ep_num == episode_number:
                    episode = library_episode
                    break
                    
        return episode
        
    def get_url(self):
        '''Return the URL of this Channels DVR server.'''
        return self.url
        
    def set_ip_address(self, ip_address):
        '''Set the server's IP address to the given one.'''
        self.ip_address = ip_address
        
    def set_port_number(self, port_number):
        '''Set the server's port number to the given one.'''
        self.port_number = port_number
        
    def skip_recording(self, job):
        '''Mark the given job as skipped in the schedule.'''
        job_id = job['ID']
        url_skip = f'{self.url}/dvr/jobs/{job_id}/skip'
        
        requests.put(url_skip)
        
class Program:
    '''
    Attributes and methods to handle one program, which may be either a scheduled
    recording or a program from the library.
    '''
    def __init__(self, program_json):
        '''Initialize the attributes of the program.'''
        self.program = program_json
        self.director       = self._get_director_from_json()
        self.episode_number = self._get_episode_number_from_json()
        self.episode_title  = self._get_episode_title_from_json()
        self.release_year   = self._get_release_year_from_json()
        self.season_number  = self._get_season_number_from_json()
        self.title          = self._get_title()
        
    def _get_director_from_json(self):
        '''Extract the first director name, if it exists, from the json data.'''
        director = None
        
        directors = self.program['Airing'].get('Directors', None)
        
        if directors:
            director = directors[0]
        
        return director
        
    def _get_episode_number_from_json(self):
        '''Extract the episode number, if it exists, from the json data.'''
        return self.program['Airing'].get('EpisodeNumber', None)
        
    def _get_episode_title_from_json(self):
        '''Extract the episode title, if it exists, from the json data.'''
        return self.program['Airing'].get('EpisodeTitle', None)
        
    def _get_release_year_from_json(self):
        '''Extract the release year, if it exists, from the json data.'''
        return self.program['Airing'].get('ReleaseYear', None)
        
    def _get_season_number_from_json(self):
        '''Extract the season number, if it exists, from the json data.'''
        return self.program['Airing'].get('SeasonNumber', None)

    def _get_title(self):
        '''Extract the program title from the json data.'''
        raw_info = self.program['Airing'].get('Raw', None)
            
        if not raw_info:
            title = self.program['Airing']['Title']
        else:
            program_info = raw_info.get('program', None)
            if not program_info:
                title = self.program['Airing']['Title']
            else:
                title = program_info['title']
    
        return title
        
    def get_program_type(self):
        '''Return "episode", "movie" or None.'''
        program_type = None
        
        if self.is_an_episode():
            program_type = "Episode"
            
        if self.is_a_movie():
            program_type = "Movie"
            
        return program_type

    def is_in_library(self, library_files=None):
        '''Return True or False: True when the given program is present in the library.'''
        in_library = False
        
        if self.is_a_movie():
            if self.is_movie_in_library(library_files):
                in_library = True
                
        if self.is_an_episode():
            if self.is_episode_in_library(library_files):
                in_library = True
            
        return in_library
        
    def is_episode_in_library(self, library_files=None):
        '''
        Return True when an episode in the library meets these conditions:
         - same exact title as the given episode
         - same season number as the given episode
         - same episode number as the given episode
         - same episode title as the given episode
        '''
        has_same_episode_title  = False
        
        library_episode = dvr.get_one_episode_of_one_series_from_library(self.title, self.season_number, self.episode_number, library_files)

        if library_episode:
            library_episode = Program(library_episode)
            if library_episode.episode_title:
                try:
                    has_same_episode_title = library_episode.episode_title.lower() == self.episode_title.lower()
                except Exception:
                    print(self.title)
                    print(self.episode_title)
                    print(library_episode.episode_title)
                    raise RuntimeError

        return has_same_episode_title

    def is_a_manual_recording(self):
        '''Return True or False: True if the ID tag contains "-ch".'''
        scheduled_manually = "-ch" in self.program['ID']

        if not scheduled_manually:
            job_id = self.program.get('JobID', None)

            if job_id:
                scheduled_manually = "-ch" in job_id

        return scheduled_manually
    
    def is_a_movie(self):
        '''Return True or False: True if the given program is categorized as a movie.'''
        is_movie = False
        
        categories = self.program['Airing'].get('Categories', None)
        
        if categories:
            is_movie = 'Movie' in categories

        return is_movie
        
    def is_movie_in_library(self, library_files=None):
        '''
        Return True or False: True if one movie in the library matches:
         - the same exact title
         - the same year of release
         - the same director
        '''
        has_same_release_year = False
        has_same_director     = False
        
        library_movie = dvr.get_one_movie_from_library(self.title, library_files)
        
        if library_movie:
            has_same_release_year = library_movie['Airing']['ReleaseYear'] == self.release_year
            has_same_director     = self.director in library_movie['Airing']['Directors']

        return has_same_release_year and has_same_director
        
    def is_recording_in_progress(self):
        '''
        If a scheduled recording has already been assigned a file ID, this means that 
        the recording is in progress. Return True is this is the case.
        '''
        in_progress = False
        
        file_id = self.program['FileID']
        if file_id:
            in_progress = True
        
        return in_progress

    def is_an_episode(self):
        '''Return True or False: True if the given program is categorized as a series.'''
        is_episode = False
        
        categories = self.program['Airing'].get('Categories', None)
        
        if categories:
            is_episode = ('Episode' in categories) or \
                         ( ('Series' in categories) and (self.season_number != None) and (self.episode_number != None) )
        else:
            episode_title = self.program['Airing'].get('EpisodeTitle', None)
            
            if episode_title:
                is_episode = True

        return is_episode
        
    def skip_recording(self):
        '''Tell the DVR to skip the recording of this program.'''
        dvr.skip_recording(self.program)

        
# Create a generic Channels DVR server instance
dvr = ChannelsDVRServer()