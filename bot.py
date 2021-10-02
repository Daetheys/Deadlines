import discord
import os
import numpy as np
import datetime
import traceback
import pickle
import re

f = open('logs.txt', 'a+')
def log(f,*txt):
    f.write(str(datetime.datetime.now())+" - ")
    if len(txt)== 1:
        f.write(str(txt[0])+'\n')
    else:
        f.write(str(txt)+'\n')
    f.flush()

#Ugly but fast to write
def print(*args):
    return log(f,*args)

client = discord.Client()

first_time = False #Init pickle databases

MAXIDN = 10**5

default_emote = '🟦'
missing_emote = '🟥' #Shouldn't be used in practice

#courses_dict = {}

#deadlines_dict = {}

channel = None

#-------------------------------------------
#
#           Manage Course Functions
#
#-------------------------------------------
def load_courses():
    with open('courses.p','rb') as f:
        l = pickle.load(f)
        return l

def save_courses(courses):
    with open('courses.p','wb') as f:
        pickle.dump(courses,f)

def add_course(course,emote):
    #Add new course
    if len(emote)>2:
        error('An emote or a short message (max 2 chars) is supposed to be given : got {}'.format(emote))
        return 0
    courses_dict = load_courses()
    try:
        courses_dict[course]
        error('Course {} already exists.'.format(course))
        return 0
    except KeyError:
        courses_dict[course] = emote
        save_courses(courses_dict)
        return 1

def remove_course(course):
    #Remove activity of course
    ld = deadlines_for_course(course)
    if len(ld) != 0:
        error('Cannot delete course because it is linked to existing deadlines')
    courses_dict = load_courses()
    try:
        del courses_dict[course]
        save_courses(courses_dict)
    except KeyError:
        error("Course {} doesn't exists.".format(course))
    return 1

def update_course_emote(course,emote):
    courses_dict = load_courses()
    try:
        courses_dict[course] = emote
        save_courses(courses_dict)
        return 1
    except KeyError:
        error("Course {} doesn't exists.".format(course))

def format_course(course,emote):
    return emote + ' ' + course

def list_courses():
    courses_dict = load_courses()
    s = '```\n'
    for c in courses_dict.keys():
        s += format_course(c,courses_dict[c]) + '\n'
    s += '```'
    return s

#-------------------------------------------
#
#           Manage Deadlines Functions
#
#-------------------------------------------
def load_deadlines():
    with open('deadlines.p','rb') as f:
        return pickle.load(f)

def save_deadlines(dl):
    with open('deadlines.p','wb') as f:
        pickle.dump(dl,f)

def get_idn(deadlines_dict): #Generates a new ID for the deadline
    idn = np.random.randint(0,10**5) # 5 digits ID
    while idn in deadlines_dict.keys(): #Verifies it doesn't already exists
        idn = np.random.randint(0,10**5)
    return idn

def add_deadline(d,course_name,obj): #Add new deadline
    #Check and completes the date
    now = datetime.datetime.today()
    if d.count('/') == 1: #Day/month format -> will guess the year
        #Parse the day/month format
        try:
            dat = datetime.datetime.strptime(d,'%d/%m')
        except ValueError:
            error('Unknown date {}.'.format(d))
            return 0 #Deadline not added
        #guess the year
        dat = dat.replace(year=now.year) #Try this year
        if dat < now: #If this year doesn't match -> put next year
            dat = dat.replace(year=now.year+1)
    elif d.count('/') == 2: #Day/month/year format
        #Parse the day/month/year format
        try:
            dat = datetime.datetime.strptime(d,'%d/%m/%Y')
        except ValueError:
            error('Unknown date {}.'.format(d))
            return 0 #Deadline not added
    else:
        error('First parameter is supposed to be a date ($add {DATE} {COURSE} {OBJECT}). Got {} but expect a DD/MM or DD/MM/YYYY format.'.format(d))
    #Checks the course
    courses_dict = load_courses()
    try:
        courses_dict[course_name]
    except KeyError:
        error('Second parameter is supposed to be a course. Got {} but this course isn\'t in the database (type $listcourses to see available courses).'.format(course_name))
    #Get the deadlines
    deadlines_dict = load_deadlines()
    #Check if a deadline with this date and course already exists
    warning_msg = None
    for k in deadlines_dict:
        print(deadlines_dict[k])
    print(d,course_name)
    if check_already_existing_dl(dat,course_name,deadlines_dict):
        s = "A deadline for course {} at date {} already exists. \
If you have created this deadlines twice because you didn't see it using $show, use $showall \
to see all deadlines.".format(course_name,d)
        warning_msg = s
    print(warning_msg)
    #Adds the deadline with valid date and course
    idn = get_idn(deadlines_dict) #Get a fresh id
    deadlines_dict[idn] = (dat,course_name,obj)
    #Save the deadlines
    save_deadlines(deadlines_dict)
    return 1,idn,warning_msg #Deadline added

def check_already_existing_dl(date,course,deadlines_dict):
    l = deadlines_for_course(course,deadlines_dict=deadlines_dict)
    for d,c,o in l:
        if d == date:
            return True
    return False
    
def remove_deadline(idn):
    deadlines_dict = load_deadlines()
    try:
        del deadlines_dict[int(idn)]
        save_deadlines(deadlines_dict)
    except KeyError:
        error('Unknown id {}.'.format(idn))
        return 0
    return 1

def deadlines_for_course(course,deadlines_dict=None):
    if deadlines_dict is None:
        deadlines_dict = load_deadlines()
    l = []
    for idn in deadlines_dict.keys():
        d,c,o = deadlines_dict[idn]
        if c == course:
            l.append((d,c,o))
    return l

def sort_deadlines(dl):
    return sorted(dl,key=lambda v : v[0])

def select_deadlines(dl):
    sdl = sort_deadlines(dl)
    print('sorted deadlines :')
    for i in sdl:
        print(i)
    now = datetime.datetime.today()
    passed = []
    future = []
    for d in sdl:
        if d[0]<now:
            passed.append(d)
        else:
            future.append(d)
    print('passed')
    for i in passed:
        print(i)
    print('future')
    for i in future:
        print(i)
    #passed.reverse()
    return passed[-5:]+future[:15]


def format_deadline(dl,courses_dict):
    course_name_size = 20
    obj_text_size = 30
    (d,course_name,obj,idn) = dl
    s = ('0' if d.day < 10 else '')+str(d.day)+'/'+('0' if d.month < 10 else '')+str(d.month) + ' '*3
    try:
        emote = courses_dict[course_name]
    except KeyError:
        emote = missing_emote
    cname = course_name[:course_name_size] + ' '*(course_name_size-len(course_name))
    obj_txt = obj[:obj_text_size] + ' '*(obj_text_size-len(obj))
    s += emote + ' ' + cname + ' '*3 + obj_txt + ' '*3 + str(idn)
    return s

def get_deadlines_str(all=False,filtercourse=None):
    deadlines_dict = load_deadlines()
    print("show deadlines :")
    for k in deadlines_dict:
        print(k,deadlines_dict[k])
    courses_dict = load_courses()
    if all:
        selected_deadlines = sort_deadlines([(*deadlines_dict[i],i) for i in deadlines_dict.keys()])
        nb_messages = len(selected_deadlines)//20+(1 if len(selected_deadlines)%20!=0 else 0)
        lselected_deadlines = [selected_deadlines[20*i:20*(i+1)] for i in range(nb_messages)]
    else:
        lselected_deadlines = [select_deadlines([(*deadlines_dict[i],i) for i in deadlines_dict.keys()])]

    ls = []
    for selected_deadlines in lselected_deadlines:
        s = '```diff\n'
        s += 'Date '+' '*3+' '+' '+'       Course       '+' '*3+"            Object            "+" "*3+"   Id  "+"\n"
        for dl in selected_deadlines:
            #Strikethrough if deadline is over
            s += ("-" if dl[0] < datetime.datetime.today() else " ") + format_deadline(dl,courses_dict) +'\n'
        s += '```'
        ls.append(s)
    return ls

#-------------------------------------------
#
#              Parsing Functions
#
#-------------------------------------------

def parse(c):
    print("PARSING :",c)
    p1 = re.findall('^\$([a-zA-Z0-9_]+)((?: -[a-zA-Z0-9_/\-]+ [a-zA-Z0-9_/\-\U00010000-\U0010ffff]*)*)((?: [a-zA-Z0-9_/\-\U00010000-\U0010ffff]+| "[a-zA-Z0-9_/\- \U00010000-\U0010ffff]+")*)$',c)
    print("AFTER 1st STEP :",p1)
    if len(p1) != 1:
        return None

    p1 = p1[0]

    command = p1[0]
    params_str = p1[1]
    args_str = p1[2]
    print("AFTER SECOND STEP :",c,command,params_str,args_str)
    params = re.findall('-([a-zA-Z0-9_/\-]+) ([a-zA-Z0-9_/\-\U00010000-\U0010ffff]*)',params_str)

    args = re.findall('(?: ([a-zA-Z0-9_/\-\U00010000-\U0010ffff]+|"[a-zA-Z0-9_/ \-\U00010000-\U0010ffff]+"))',args_str)

    for i in range(len(args)):
        if args[i][0] == '"':
            args[i] = args[i][1:-1]

    return command,params,args

def setup_params(d_init,params,command_name):
    #Put given params in the dictionary and prints an error if unkown params are given
    for e in params:
        attr = e[0]
        if attr in d_init.keys():
            value = e[1]
            if value is None:
                d_init[attr] = True
            else:
                d_init[attr] = type(d_init[attr])(value)
        else:
            error('Unknown parameter {} for command {}'.format(attr,command_name))
    return 1

def verify_nb_args(args,nb,command_name):
    if len(args) != nb:
        error('Command {} is supposed to get {} params'.format(command_name,nb))
    return 1

#-------------------------------------------
#
#          Messages Alert Functions
#
#-------------------------------------------
class ErrorException(Exception):
    def __init__(self,m,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.m = m

def error(msg):
    raise ErrorException(msg)

async def warning(msg,channel):
    print('WARNING : ', msg)
    msg = '```fix\n WARNING : '+msg+'```'
    await channel.send(msg)

async def confirmation(msg,channel):
    print('CONFIRMATION :', msg)
    msg = '```yaml\n'+msg+'```'
    await channel.send(msg)

#-------------------------------------------
#
#                Bot Functions
#
#-------------------------------------------

@client.event
async def on_ready():
    print('logged in')

@client.event
async def on_message(m):
    try:
        #Doesn't respond to its own messages
        if m.author == client.user:
            return
        #Responds to messages starting with a '$'
        if m.content.startswith('$'):
            
            print('-------------------------------------')
            print('              NEW INPUT              ')
            print('-------------------------------------')

            v = parse(m.content)

            try: #Custom Errors handling
                if v is None:
                    error('Your command doesn\'t respect the format : type $help to see commands\' format')
                (command,params,args) = v
                print('INPUT : ',command,params,args)

                #-- AddCourse Command
                if command == 'newcourse':
                    d = {'emote':default_emote}
                    if setup_params(d,params,'newcourse') and verify_nb_args(args,1,'newcourse') and add_course(args[0],d['emote']):
                        await confirmation('Course {} {} added'.format(d['emote'],args[0]),m.channel)

                elif command == 'updatecourse':
                    d = {}
                    if setup_params(d,params,'updatecourse') and verify_nb_args(args,2,'updatecourse') and update_course_emote(args[0],args[1]):
                        await confirmation('Course {} {} updated'.format(args[1],args[0]),m.channel)

                #-- DeleteCourse Command
                elif command == 'deletecourse':
                    d = {}
                    if setup_params(d,params,'deletecourse') and verify_nb_args(args,1,'deletecourse') and remove_course(args[0]):
                        await confirmation('Course {} deleted'.format(args[0]),m.channel)

                #-- ListCourse Command
                elif command == 'listcourses':
                    d = {}
                    if setup_params(d,params,'listcourse') and verify_nb_args(args,0,'listcourse'):
                        s = list_courses()
                        await m.channel.send(s)

                #-- AddDeadline Command
                elif command == 'add':
                    d = {}
                    if setup_params(d,params,'add') and verify_nb_args(args,3,'add'):
                        b,idn,warning_msg = add_deadline(*args)
                        if b:
                            await confirmation('Deadline no {} created'.format(idn),m.channel)
                        #Check already existing deadlines at this date (won't block the creation but will send a warning)
                        if warning_msg:
                            await warning(warning_msg,m.channel)
                        

                #-- RemoveDeadline Command
                elif command == 'remove':
                    d = {}
                    if setup_params(d,params,'remove') and verify_nb_args(args,1,'remove') and remove_deadline(args[0]):
                        await confirmation('Deadline no {} removed'.format(args[0]),m.channel)

                #-- Show Command
                elif command == 'show':
                    d = {'filtercourse':None}
                    if setup_params(d,params,'show') and verify_nb_args(args,0,'show'):
                        s = get_deadlines_str(all=False,filtercourse=d['filtercourse'])[0]
                        await m.channel.send(s)
                elif command == 'showall':
                    d = {}
                    if setup_params(d,params,'showall') and verify_nb_args(args,0,'showall'):
                        ls = get_deadlines_str(all=True)
                        for s in ls:
                            await m.channel.send(s)
                elif command == 'help':
                    msg = "```md\n\
#Welcome to the Deadline Bot. This bot makes it possible to track deadlines for the whole class.\n\
#Here are few commands you can use. Commands are given between [] where {} represents parameters and () optional parts of commands. A short description of what the command is used for is then given between ().\n\n\
-- <A Courses_Management> : \n\
1. [$newcourse (-emote {emote}) {coursename}]( to add a new course)  \n\
> Example : $newcourse -emote 🧠 transfert-learning \n\
2. [$updatecourse {coursename} {emote}]( to update the emote of an existing course) \n\
> Example : $updatecourse transfert-learning 📖 \n\
3. [$deletecourse {coursename}]( to delete an existing course - won't work if deadlines are still linked to this course) \n\
> Example : $deletecourse transfert-learning \n\
4. [$listcourses]( to list all existing courses) \n\
> Example : $listcourses \n\n\
-- <B Deadlines_Management> : \n\
1. [$add {date} {coursename} {obj}]( to add a new deadline. date's format must either be DD/MM - in this situation the bot will complete the year as the current year or the next one so that the given date hasn't passed - or DD/MM/YYYY if you want to specify the date) \n\
> Example : $add 27/11 transfert-learning \"New Homework\" \n\
2. [$remove {id}]( to remove a specific deadline) \n\
> Example : $remove 85628 \n\
3. [$show]( to show existing deadlines (capped at 20 deadlines : 5 passed - for people who are late - and 15 next)\n\
> Example : $show \n\
4. [$showall]( to show all deadlines)\n\
> Example : $showall \n\
```"
                    await m.channel.send(msg)
                else:
                    error('Unknown command {}. Type $help to get the list of commands'.format(command))

            except ErrorException as e:
                msg = '```diff\n- '+e.m+'```'  #For a red message
                await m.channel.send(msg)
    except Exception as e:
        print(traceback.format_exc())
        msg = '```diff\n- Internal Error : sorry for the inconvenience. @Daetheys pls fix this.```'
        await m.channel.send(msg)

first_time = False #Just an additional security
if first_time:
    save_courses({})
    save_deadlines({})

import pw
client.run(pw.pw)
f.close()