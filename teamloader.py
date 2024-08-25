#!/bin/env python3

import requests as req
import pandas as pd
import re
import json
import sys


conf = json.load(open('config.json'))

access_token = conf['access_token']
org_name = conf["org_name"]
course = conf["course"]
term = conf["term"]

delete_allowed = False # KEEP THIS FALSE UNLESS YOU NEED TO DELETE REPOS

headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def gh_get(path):
    return req.get(f'https://api.github.com{path}', headers=headers)

def gh_post(path, data):
    #print(path)
    #print(data)
    resp = req.post(f'https://api.github.com{path}', json=data, headers=headers)
    #print(resp)
    return resp

def in_org(username):
    resp = gh_get(f'/orgs/{org_name}/members/{username}')
    if resp.status_code not in [204, 404]:
        raise Exception('bad resp code')
    return resp.status_code == 204

def get_uid_from_username(username):
    resp = gh_get(f'/users/{username}')
    if resp.status_code == 404: return None
    return resp.json()['id']

def get_tid_from_team_number(number):
    resp = gh_get(f'/orgs/{org_name}/teams/{term}-{number:02d}')
    return resp.json()['id']

def create_team(number):
    resp = gh_post(f'/orgs/{org_name}/teams', {'name': f'{term}-{number:02d}', 'repo_names': [f'{org_name}/RBE{course}_{term}_Team{number:02d}'], 'permission': 'push'})
    if resp.status_code != 201: raise Exception('team creation failed')

def create_repo(team_number):
    resp = gh_post(f'/repos/{org_name}/{course}-Template/generate', {'owner': org_name, 'name': f'RBE{course}_{term}_Team{team_number:02d}', 'private': True})
    if resp.status_code != 201: raise Exception('repo creation failed')

def delete_repo(name):
    if not delete_allowed: raise Exception('no deleting repos without permission!') # if you delete this line you are a monster
    resp = req.delete(f'https://api.github.com/repos/{org_name}/{name}', headers=headers)
    #print(resp)
    if resp.status_code != 204: raise Exception('repo deletion failed')

def purge_teams():
    if not delete_allowed: raise Exception('no deleting teams without permission!')
    resp = gh_get(f'/orgs/{org_name}/teams')
    slugs = [team['slug'] for team in resp.json()]
    for slug in slugs:
        resp = req.delete(f'https://api.github.com/orgs/{org_name}/teams/{slug}', headers=headers)
        if resp.status_code != 204: raise Exception('team deletion failed')

def get_course_repos(course, term=None):
    resp = gh_get(f'/orgs/{org_name}/repos')
    repos = [repo['name'] for repo in resp.json()]
    if term == None: term = "\\w\\d{2}"
    repos = list(filter(lambda x: re.match(f'^RBE{course}_{term}_Team\\d{{2}}$', x) != None, repos))
    return(repos)

def invite_user(user_id, team_number):
    resp = gh_post(f'/orgs/{org_name}/invitations', {'invitee_id': user_id, 'team_ids': [get_tid_from_team_number(team_number)]})
    if resp.status_code != 201: raise Exception(f'problem inviting {user_id}')

def build_repos_and_teams(users):

    teams = users['Team'].unique()
    print(f'building teams: {teams}')
    for team in teams:
        create_repo(team)
        create_team(team)
        print('.', end='')
    print()

if __name__ == '__main__':
    if (sys.argv[1] == '--help'):
        print('''
        RBE 300n teamloader
        run with no arguments to invite to teams
        run with --purge-dangerously <course> <term> to remove all teams and all repos from the listed term
        ''')
    elif (sys.argv[1] == '--purge-dangerously'):
        if len(sys.argv) < 4 or re.match('^\\d{4}$', sys.argv[2]) == None or re.match('^[ABCD]\\d{2}$', sys.argv[3]) == None:
            raise Exception('read the instructions lol')
        delete_allowed = True
        repos = get_course_repos(sys.argv[2], sys.argv[3])
        print(repos)
        for repo in repos:
            delete_repo(repo)
        purge_teams()
        delete_allowed = False
    
    else:
        users = pd.read_csv('merged.csv')
        users.drop(columns=['Unnamed: 0'], inplace=True)

        #build_repos_and_teams(users) # run with this uncommented ONCE

        gitusers = users.dropna()
        print('getting user ids....')
        gitusers['github_id'] = gitusers.apply(lambda row: get_uid_from_username(row['GitHub Username']), axis=1)
        print('\n\n\nTHE FOLLOWING USERS HAVE BAD NAMES:')
        bad_names = gitusers.loc[gitusers.isnull().any(axis=1)]
        print(bad_names)
        print('\n\n\n')
        gitusers = gitusers.dropna()
        gitusers.github_id = gitusers.github_id.astype(int)
        print(gitusers)
        print('inviting users...', end='')
        for _, user in gitusers.iterrows():
            if not in_org(user['GitHub Username']):
                #print(f'adding {user.github_id}')
                invite_user(user.github_id, user['Team']);
                print('.', end='', flush=True)
            else:
                print(f'{user["GitHub Username"]} is already in the repo!')
        print('done inviting!')