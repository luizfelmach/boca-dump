#!/bin/python3

from hashlib import sha256
from bs4 import BeautifulSoup
from getpass import getpass
import requests
import multiprocessing
import os
import sys

BOCA_HOST = "https://boca.pet.inf.ufes.br/boca"  # BOCA do PET
# BOCA_HOST = "http://200.137.66.69/boca/"       # BOCA do Thiago


class Boca:

    def __init__(self, user, password):
        self.user = user
        self.password = self.hash256(password)
        self.uri = BOCA_HOST
        self.session = requests.Session()
        self.login()
        self.runs = self.get_runs()
        self.output_path = "output"

    def login(self):
        session_hash = self.hash256(self.password + self.get_cookie_hash())
        self.get(f"index.php/?name={self.user}&password={session_hash}")
        if not self.is_auth():
            print("ValueError: invalid user or password (only admin)")
            exit(1)
        print("Successfully authenticated")

    def get_run_path(self, runnumber, runsitenumber = 1):
        response = self.get(f"admin/runedit.php?runnumber={runnumber}&runsitenumber={runsitenumber}")
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find_all("table")[2]
        path = table.find_all("tr")[5].find("a")["href"].replace("../", "")
        return path

    def print_run(self, run):
        print(run["runnumber"], end="")
        print("\033[1A")

    def get_run_thread(self, run):
        self.print_run(run)
        return self.get_run_path(run["runnumber"], run["runsitenumber"])

    def get_runs(self):
        runs = []

        response = self.get(f"admin/run.php")

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find_all("table")[2];
        runs_soup = table.find_all("tr")[1::]

        for run_soup in runs_soup:
            line_soup = run_soup.find_all("td")
            runnumber = int(line_soup[0].text)
            runsitenumber = int(line_soup[1].text)
            user = line_soup[2].text
            time = int(line_soup[3].text)
            problem = line_soup[4].text
            lang = line_soup[5].text
            answer = line_soup[9].text
            run = {
                "runnumber": runnumber,
                "runsitenumber": runsitenumber,
                "user": user,
                "time": time,
                "problem": problem,
                "lang": lang,
                "answer": answer,
            }
            runs.append(run)

        print("Get file path")
        pool = multiprocessing.Pool()
        results = pool.map(self.get_run_thread, runs)
        pool.close()
        pool.join()
        print()

        i = 0
        for result in results:
            runs[i]["path"] = result
            i += 1

        return runs
    

    def save_run_thread(self, run):
        self.print_run(run)
        response = self.get(run["path"])
        output = f"{self.output_path}/{self.file_name(run)}"
        with open(output, "wb") as file:
            file.write(response.content)

    def save_runs(self, output):
        self.output_path = output
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
        print("Saving file")
        pool = multiprocessing.Pool()
        pool.map(self.save_run_thread, self.runs)
        pool.close()
        pool.join()
        print()

    def file_name(self, run):
        return f"{run['user']}-{run['runnumber']}-{run['problem']}-{run['answer']}.c"

    def get(self, path):
        response = self.session.get(f"{self.uri}/{path}")
        return response

    def get_cookie_hash(self):
        res = self.get("/")
        sessId = res.cookies.get("PHPSESSID")
        return sessId

    def is_auth(self):
        response = self.get("admin/index.php")
        if "Username:" in response.text:
            return True
        if "Session expired. You must log in again." in response.text:
            return False
        if "Violation (admin/index.php). Admin warned." in response.text:
            return False
        return False
    
    def hash256(self, string):
        return sha256(string.encode('utf-8')).hexdigest()

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print(f"usage: {sys.argv[0]} <output_path>")
        exit(0)
    user = input('User: ')
    password = getpass('Password: ')
    nav = Boca(user, password)
    nav.save_runs(sys.argv[1]) # pasta onde sera salvo
