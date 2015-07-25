
#############################

#Usage: in command line type 

# python p3_processor.py "" P3-14-02-27.txt  

# If there is no password else python p3_processor.py 1234 P3-14-02-27.txt  (if password 1234)

#############################

import re
import sys
import os
import MySQLdb

Host =  "localhost"
Username =  "root"
Password = ""
Database =  "ammes_main"
Port =  "3306"

def extract_data(filename):
  """
  Given a file name for , Parses the Date, ClaimNo, Physician, Amount
    
  """
  # print Password
    
  # Open and read the file.
  with(open(filename, 'rU')) as f:
    text = f.read()
    
    date_match = re.search(r'PREPARED\s*\d{2,4}\s*\d{2}\s*\d{2}', text)    
    if not date_match:
      # We didn't find a date, so we'll exit with an error message.
      sys.stderr.write('Couldn\'t find the accept_date!\n')
      sys.exit(1)

    p3_accept_date = date_match.group()    

    #Getting 1st Claim No from File
    first_clm_no_match = re.search(r'1ST CLM# \d{9}', text)
    if not first_clm_no_match:
      # We didn't find a Claim No, so we'll exit with an error message.
      sys.stderr.write('Couldn\'t find the Column No!\n')
      sys.exit(1)
    first_clm_no = first_clm_no_match.group()
    first_clm_no = first_clm_no.split('# ')    
    if first_clm_no:
      first_clm_no = first_clm_no[1]

    #Getting Physician No's 
    physician_match = re.findall(r'PHYSICIAN \d{5} ',text)
    if not physician_match:
      # We didn't find a year, so we'll exit with an error message.
      sys.stderr.write('Couldn\'t find the Physician!\n')
      sys.exit(1)
    physician_no = physician_match
    # print physician_match
    
    #Getting Fees Submitted
    fee_submitted_match = re.findall(r'TOTAL FEE SUBMITTED\s*\$(\d*[,]*\d*\.\d*|\d*[,]*\d*|\d*\.\d*|\d*)?',text)
    if not fee_submitted_match:
      # We didn't find a year, so we'll exit with an error message.
      sys.stderr.write('Couldn\'t find the Physician!\n')
      sys.exit(1)

    # print fee_submitted_match
    
    """ Mysql Work Starts Here """

    #Connectiong to database
    try:
      db = MySQLdb.connect(host=Host, # your host, usually localhost
               user=Username, # your username
                passwd=Password, # your password
                db=Database) # name of the data base    
    except:
      sys.stderr.write('Couldn\'t Connect to database!\n')
      sys.exit(1)

    cur = db.cursor()

    #Step 1 Getting the submission id and storing in a variable
    query = "SELECT submission_id FROM claims WHERE claims.manitoba_health_claim_id = %s" %  first_clm_no    
    submission_id = None
    try:
      cur.execute(query)    
      submission_id = [item[0] for item in cur.fetchall()]       
      if submission_id:
        submission_id = submission_id[0]            
      else:
        sys.stderr.write('Couldn\'t find submission id for given ClaimNo! %s \n' % first_clm_no)
        sys.exit(1)
    except MySQLdb.Error as errorMessage:
      sys.stderr.write(errorMessage)
      sys.exit(1)
 

    """ Step2 Updating the Submissions Record """    
    #Formatting date for Mysql
    from datetime import datetime
    p3_accept_date = datetime.strptime(p3_accept_date.split('  ')[1], "%y %m %d")  
    if submission_id:  
      query = "UPDATE submissions SET p3_accept_date='{0}',first_claim_number={1} WHERE submission_id={2}".format(p3_accept_date,first_clm_no,submission_id)
      print query

    try:
      cur.execute(query)
    except MySQLdb.Error as errorMessage:
      sys.stderr.write(errorMessage)
      sys.exit(1)

    """ Step3-a physician_ids based on the practitioner_numbers """
    physician_ids = []    
    practitioner_numbers = list(set([re.sub('PHYSICIAN ','',p_no).strip() for p_no in physician_no]))
    for p_no in list(set([re.sub('PHYSICIAN ','',p_no).strip() for p_no in physician_no])):
      query = "SELECT physician_id FROM physicians WHERE practitioner_number={0}".format(p_no)
      print query
      try:
        cur.execute(query)
        physician_id = [item[0] for item in cur.fetchall()][0]        
        physician_ids.append(physician_id)
      except MySQLdb.Error as errorMessage:
        sys.stderr.write(errorMessage)
        sys.exit(1)
    print physician_ids

    """ STEP3-b """
    for p_no,physician_id in enumerate(physician_ids):
      if submission_id:
        query = "INSERT INTO submission_lines VALUES(DEFAULT,{0},{1},{2},{3})".format(submission_id,physician_id,practitioner_numbers[p_no],fee_submitted_match[p_no].replace(',',''))
      try:
        cur.execute(query)
        db.commit()
      except MySQLdb.Error as errorMessage:
        sys.stderr.write(errorMessage)
        sys.exit(1)
      
    """ STEP4 Deleting File if processed Successfully """
    if os.path.isfile(filename):      
      os.remove(filename)
    else:    ## Show an error ##
      sys.stderr.write("Error: %s file not found" % filename)

    # sys.exit(1)


def main():
  if len(sys.argv) != 3:
    print 'usage: ./P3_processor.py MySQLPassword Inputfile'
    sys.exit(1)

  global Password
  Password = sys.argv[1]
  filename = sys.argv[2]
  
  extract_data(filename)
  
  sys.exit(1)

if __name__ == '__main__':
  main()
  

if sys.platform == 'win32':
    base = 'Win32GUI'