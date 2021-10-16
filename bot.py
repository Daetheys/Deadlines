import discord
import os
import numpy as np
import datetime
import traceback
import pickle
import re

online_mode = True

f = open('logs.txt', 'a+')
def log(*txt):
    if online_mode:
        print(*txt)
        return
    f.write(str(datetime.datetime.now())+" - ")
    if len(txt)== 1:
        f.write(str(txt[0])+'\n')
    else:
        f.write(str(txt)+'\n')
    f.flush()

client = discord.Client()

MAXIDN = 10**5

default_emote = '🟦'
missing_emote = '🟥' #Shouldn't be used in practice

#-------------------------------------------
#
#           Manage Course Functions
#
#-------------------------------------------
def load_courses():
    #Load the courses list from database
    with open('courses.p','rb') as f:
        l = pickle.load(f)
        return l

def save_courses(courses):
    #Save the courses list in the database
    with open('courses.p','wb') as f:
        pickle.dump(courses,f)

def add_course(course,emote):
    #Add new course
    if len(emote)>2:
        error('An emote or a short text (max 2 chars) is supposed to be given : got {}'.format(emote))
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
    #Update the emote associated to the given course and saves it in the database
    courses_dict = load_courses()
    try:
        courses_dict[course] = emote
        save_courses(courses_dict)
        return 1
    except KeyError:
        error("Course {} doesn't exists.".format(course))

def format_course(course,emote):
    #Transforms a course and an emote into a str to print
    return emote + ' ' + course

def list_courses():
    #Returns the formatted string of the list of all the courses
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
    #Returns the deadline database
    with open('deadlines.p','rb') as f:
        return pickle.load(f)

def save_deadlines(dl):
    #Save the deadline database
    with open('deadlines.p','wb') as f:
        pickle.dump(dl,f)

def get_idn(deadlines_dict): #Generates a new ID for the deadline
    #Returns a fresh ID for a new deadline
    idn = np.random.randint(0,10**5) # 5 digits ID
    while idn in deadlines_dict.keys(): #Verifies it doesn't already exists
        idn = np.random.randint(0,10**5)
    return idn

def parse_date(d):
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
        error('First parameter is supposed to be a date ($add DATE COURSE OBJECT). Got {} but expect a DD/MM or DD/MM/YYYY format.'.format(d))
    return dat

def add_deadline(d,course_name,obj): #Add new deadline
    #Check and completes the date
    dat = parse_date(d)
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
        log(deadlines_dict[k])
    log(d,course_name)
    if check_already_existing_dl(dat,course_name,deadlines_dict):
        s = "A deadline for course {} at date {} already exists. \
If you have created this deadlines twice because you didn't see it using $show, use $showall \
to see all deadlines.".format(course_name,d)
        warning_msg = s
    log(warning_msg)
    #Adds the deadline with valid date and course
    idn = get_idn(deadlines_dict) #Get a fresh id
    deadlines_dict[idn] = (dat,course_name,obj)
    #Save the deadlines
    save_deadlines(deadlines_dict)
    return 1,idn,warning_msg #Deadline added

def check_already_existing_dl(date,course,deadlines_dict):
    #Check if the deadline already exists in the given database
    l = deadlines_for_course(course,deadlines_dict=deadlines_dict)
    for d,c,o in l:
        if d == date:
            return True
    return False
    
def remove_deadline(idn):
    #Removes a deadline from the database and saves
    try:
        idn = int(idn)
    except ValueError:
        error("Please enter a number for the deadline id.")
    deadlines_dict = load_deadlines()
    try:
        del deadlines_dict[idn]
        save_deadlines(deadlines_dict)
    except KeyError:
        error('Unknown id {}.'.format(idn))
        return 0
    return 1

def update_deadline(idn,date,obj):
    #Updates the deadline with given date or obj
    try:
        idn = int(idn)
    except ValueError:
        error("Please enter a number for the deadline id.")
    if date is None and obj is None:
        error("Please either specify a new date or a new obj for the deadline")
    deadlines_dict = load_deadlines()
    try:
        deadlines_dict[idn]
    except KeyError:
        error("Unknown deadline id")
    if not(date is None):
        dat = parse_date(date)
        deadlines_dict[idn] = (dat,)+deadlines_dict[idn][1:]
    if not(obj is None):
        deadlines_dict[idn] = deadlines_dict[idn][:-1]+(obj,)
    save_deadlines(deadlines_dict)


def deadlines_for_course(course,deadlines_dict=None):
    #Extracts all deadlines associated to a course
    if deadlines_dict is None:
        deadlines_dict = load_deadlines()
    l = []
    for idn in deadlines_dict.keys():
        d,c,o = deadlines_dict[idn]
        if c == course:
            l.append((d,c,o))
    return l

def sort_deadlines(dl):
    #Sorts the given list of deadline by date
    return sorted(dl,key=lambda v : v[0])

def select_deadlines(dl):
    #Selects few deadlines to show. Will keep the latest 3 passed deadlines and the 17 next ones.
    sdl = sort_deadlines(dl)
    log('sorted deadlines :')
    for i in sdl:
        log(i)
    now = get_today()
    passed = []
    future = []
    for d in sdl:
        if d[0]<now:
            passed.append(d)
        else:
            future.append(d)
    log('passed')
    for i in passed:
        log(i)
    log('future')
    for i in future:
        log(i)
    #passed.reverse()
    return passed[-3:]+future[:17]


def format_deadline(dl,courses_dict):
    #Returns a formated string representing the given deadlines (this function doesn't sort deadlines)
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

def get_today():
    #Returns the datetime of today
    today = datetime.datetime.today()
    today = today.replace(microsecond=0,second=0,minute=0,hour=0)
    return today

def get_deadlines_str(all=False,filtercourse=None):
    #Returns an array of formatted strings representing packs of 20 deadlines. all=False only returns only one string with few selected deadlines.
    deadlines_dict = load_deadlines()
    log("show deadlines :")
    for k in deadlines_dict:
        log(k,deadlines_dict[k])
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
        s += '     Date '+' '*3+' '+' '+'       Course       '+' '*3+"            Object            "+" "*3+"   Id  "+"\n"
        today = get_today()
        for dl in selected_deadlines:
            #Color deadlines depending on time left
            if dl[0] < today:
                log(dl[0],today)
                pre = '-  '+'❌'
            elif dl[0] < today + datetime.timedelta(days=3):
                pre = '   '+'❕ '
            elif dl[0] < today + datetime.timedelta(days=14):
                pre = '+  '+'📗'
            else:
                pre = '---'+'🏴'
            s += pre + format_deadline(dl,courses_dict) +'\n'
        s += '```'
        ls.append(s)
    return ls

def get_patchnote_text():
    path = "patchnotes/"
    lfiles = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f))]
    lfiles.sort()
    log("list files",lfiles)
    fname = os.path.join(path,lfiles[-1])
    log('fname',fname)
    fpatch = open(fname,'r',encoding='utf8')
    s = fpatch.read()
    return s

#-------------------------------------------
#
#              Parsing Functions
#
#-------------------------------------------

def parse(c):
    #Extracts command name,params and args from the given command line.
    log("PARSING :",c)

    #Remove multiple spaces
    c = c.replace("  "," ")
    c = c.replace("  "," ")

    #Regex commands
    command_regex = "([a-zA-Z0-9_]+)" #simple_expression
    param_name_regex = '[a-zA-Z0-9_/\-]+' #simple_expression
    param_val_regex_1 = '[a-zA-Z0-9_/\-\U00010000-\U0010ffff]+' #classical_expressions
    param_val_regex_2 = '[a-zA-Z0-9_,/\-\[\](): \U00010000-\U0010ffff]+' #"" expressions
    arg_regex_1 = '[a-zA-Z0-9_/\-\U00010000-\U0010ffff]+' #classical expressions
    arg_regex_2 = '[a-zA-Z0-9_,/\-\[\](): \U00010000-\U0010ffff]+' #"" expressions

    #Pre parsing of the command (extracts command_name,params and args sub strings)
    p1 = re.findall('^\$'+command_regex+'((?: -'+param_name_regex+' (?:'+param_val_regex_1+'|"'+param_val_regex_2+'"))*)((?: '+arg_regex_1+'| "'+arg_regex_2+'")*)$',c)
    log("AFTER 1st STEP :",p1)
    if len(p1) != 1:
        return None

    #Extract command
    p1 = p1[0]

    #Extract each part from the command
    command = p1[0]
    params_str = p1[1]
    args_str = p1[2]
    log("AFTER SECOND STEP :",c,"| |command:"+command+"| |params_str:"+params_str+"| |args_str:"+args_str)

    #Params parsing
    params = re.findall(' -('+param_name_regex+') ((?:'+param_val_regex_1+')|(?:"'+param_val_regex_2+'"))',params_str)
    #Remove ""
    for i in range(len(params)):
        params[i] = list(params[i])
        if len(params[i][1])>0 and params[i][1][0] == '"':
            params[i][1] = params[i][1][1:-1]

    #Args parsing
    args = re.findall(' ((?:'+arg_regex_1+')|(?:"'+arg_regex_2+'"))',args_str)
    #Remove ""
    for i in range(len(args)):
        if args[i][0] == '"':
            args[i] = args[i][1:-1]

    return command,params,args

def setup_params(d_init,params,command_name):
    #Put given params in the dictionary and logs an error if unkown params are given
    for e in params:
        attr = e[0]
        if attr in d_init.keys():
            value = e[1]
            if value is None:
                d_init[attr] = True
            else:
                d_init[attr] = value
        else:
            error('Unknown parameter {} for command {}'.format(attr,command_name))
    return 1

def verify_nb_args(args,nb,command_name):
    #Verifies the number of args is the right one
    if len(args) != nb:
        error('Command {} is supposed to get {} params'.format(command_name,nb))
    return 1

#-------------------------------------------
#
#          Messages Alert Functions
#
#-------------------------------------------
class ErrorException(Exception):
    #Deadlines bot internal exception (will be catched)
    def __init__(self,m,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.m = m

def error(msg):
    #Raise an ErrorException
    raise ErrorException(msg)

async def warning(msg,channel):
    #Prints a warning in the given channel
    log('WARNING : ', msg)
    msg = '```fix\n WARNING : '+msg+'```'
    await channel.send(msg)

async def confirmation(msg,channel):
    #Prints a confirmation message in the given channel
    log('CONFIRMATION :', msg)
    msg = '```yaml\n'+msg+'```'
    await channel.send(msg)

#-------------------------------------------
#
#                Bot Functions
#
#-------------------------------------------

@client.event
async def on_ready():
    #Bot just connected
    log('logged in')

@client.event
async def on_message(m):
    #Bot gets a message
    try:
        #Doesn't respond to its own messages
        if m.author == client.user:
            return

        #Check if the channel is the right one
        if not(m.channel.id in pw.channel_id):
            return
        #Responds to messages starting with a '$'
        if m.content.startswith('$'):

            log('-------------------------------------')
            log('              NEW INPUT              ')
            log('-------------------------------------')

            v = parse(m.content)

            try: #Custom Errors handling
                if v is None:
                    error('Your command doesn\'t respect the format : type $help to see commands\' format. This error might also be trigered by a special character in the command that makes the regex parsing fail. Try rewriting your command only using letters (no accent), simple emojis, spaces, underscores and dashes.')
                (command,params,args) = v
                log('INPUT : ',command,params,args)

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

                #-- UpdateDeadline Command
                elif command == 'update':
                    d = {'date':None,'object':None}
                    if setup_params(d,params,'update') and verify_nb_args(args,1,'update'):
                        update_deadline(args[0],d['date'],d['object'])
                        await confirmation('Deadline no {} has been updated'.format(args[0]),m.channel)

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
                    #Get text from help.txt
                    fhelp = open('help.txt','r',encoding='utf8')
                    msg = fhelp.read()
                    fhelp.close()
                    #Send text in a message
                    await m.channel.send(msg)
                elif command=='patchnote':
                    d = {}
                    if setup_params(d,params,'patchnote') and verify_nb_args(args,0,'patchnote'):
                        s = get_patchnote_text()
                        await m.channel.send(s)
                else:
                    error('Unknown command {}. Type $help to get the list of commands'.format(command))

            except ErrorException as e:
                msg = '```diff\n- '+e.m+'```'  #For a red message
                await m.channel.send(msg)
    except Exception as e:
        log(traceback.format_exc())
        msg = '```diff\n- Internal Error : sorry for the inconvenience. @Daetheys pls fix this.```'
        await m.channel.send(msg)

#Connecting to the bot
import pw
client.run(pw.pw)

#Close logs
f.close()