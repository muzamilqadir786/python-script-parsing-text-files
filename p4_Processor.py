#############################

#Usage: in command line type 

# python p4_processor.py "" "P4-FEB 2014 MONTH-END.txt" y

# If there is no password else python p4_processor.py 1234 "P4-FEB 2014 MONTH-END.txt"  y        Here, 1234 is the password of database


import os
import MySQLdb
from dateutil.parser import parse
import re
import sys
import smtplib
from smtplib import SMTPException
from email.MIMEText import MIMEText

Host =  "localhost"
Username =  "root"
Password = ""
Database =  "ammes_main"
Port =  "3306"

# Creating Connection
try:
    db = MySQLdb.connect(host=Host, user=Username, passwd=Password, db=Database) 
except:
    sys.stderr.write('Couldn\'t Connect to database!\n')
    sys.exit(1)

def parse_file_data(filename,send_emails):
    with open(filename,'rU') as f:
        text = f.read()

        summary_for_date = re.sub(r'SUMMARY FOR|REMITTANCE|MONTH-END?','',re.search(r'SUMMARY FOR(.*)REMITTANCE',text).group()).strip()
        if not summary_for_date:
            # We didn't find a date, so we'll exit with an error message.
            sys.stderr.write('Couldn\'t find the summary_date!\n')
            sys.exit(1)     

        # summary_for_date = parse(summary_for_date,fuzzy=True)
        # print summary_for_date

        official_date_match = re.search(r'\d{2}-\d{2}-\d{2}?',text)
        if not official_date_match:
            # We didn't find an official date, so we'll exit with an error message.
            sys.stderr.write('Couldn\'t find the summary_date!\n')
            sys.exit(1)     
        official_date = parse(official_date_match.group())
        print official_date

        # print parse(official_date,fuzzy=True)
        practitioners_no = re.findall(r'\d{5}',text)        
        if not practitioners_no:
            # We didn't find an official date, so we'll exit with an error message.
            sys.stderr.write('Couldn\'t find the practitioner nos!\n')
            sys.exit(1)     
        print practitioners_no


        interest = re.findall(r'INTEREST\s*(.*)\n',text)
        interest = interest[-1].strip()      
        print interest
                
        payments = [' '.join(item[0].split()) for item in re.findall(r'\d{5}(.*)\s*|\d{5}(.*)\s*INTEREST(.*)',text)]
        print payments        
        payments = [re.sub(r'[^\d,(.*)]',' ',p).strip() for p in payments]
        print payments
        
        opt_chqs = [re.sub(r'\d*','',item).strip() for item in re.findall(r'\s+[a-zA-Z]{2}\s+\d+',text)]
        print opt_chqs

        interests = [' '.join(item[1].split()) for item in re.findall(r'\d{5}(.*)\s*INTEREST(.*)|\d{5}(.*)\s*',text)]
        print interests

        
        """ Mysql Work Starts Here """

              
        cur = db.cursor()

        """STEP 2 Getting physician ids as per practitioner number"""
        try:
            physician_ids = []
            physician_emails = []
            for practitioner_no in practitioners_no:
                query = "SELECT physician_id,email FROM physicians WHERE practitioner_number=%s" % practitioner_no
                print query
                cur.execute(query)
                physician_ids.append([item[0] for item in cur.fetchall()][0])
                cur.execute(query)
                physician_emails.append([item[1] for item in cur.fetchall()][0])
            if send_emails in ['y','Y']:
                send_email(physician_ids)

            # print physician_ids
            # print physician_emails
        except MySQLdb.Error as errorMessage:
            sys.stderr.write(errorMessage)
            sys.exit(1)

        """ STEP3 Inserting a Return Record for File"""
        try:
            query = """INSERT INTO returns VALUES(DEFAULT,'{0}','{1}','')""".format(summary_for_date,official_date)
            print query
            cur.execute(query)
            # db.commit()
        except MySQLdb.Error as errorMessage:
            sys.stderr.write(errorMessage)
            sys.exit(1)


        """STEP4 Inserting return_summary_lines Record"""
        try: 
            for no,practitioner_no in enumerate(practitioners_no):
                total_fees,claims_processesed,claims_pending,edit_eligibility_returns = payments[no].split()
                if interests[no]:
                    interest_total_fees,interest_claims_processesed,interest_claims_pending,interest_edit_eligibility_returns = interests[no].split()
                else:
                    interest_total_fees,interest_claims_processesed,interest_claims_pending,interest_edit_eligibility_returns = 0,0,0,0
                query = """INSERT INTO return_summary_lines VALUES(DEFAULT,{0},{1},'{2}',{3},{4},{5},{6},{7},{8})""".format(physician_ids[no],practitioner_no,opt_chqs[no],total_fees.replace(',',''),claims_processesed,claims_pending,edit_eligibility_returns,interest_total_fees,interest_claims_processesed) 
                print query
                cur.execute(query)
                # db.commit()
        except MySQLdb.Error as errorMessage:
            sys.stderr.write(errorMessage)
            sys.exit(1)

def send_email(physicianIdslist):
    #Connectiong to database
    cur = db.cursor()
    mailServer = "mail.ammes.ca"
    Port = 587
    mailServerUserName = "automation@ammes.ca"
    mailServerPassword = "odeskp4"
    sender = 'info@ammes.ca'
    Subject = "Reconciliation File Loaded"

    try:            
        for practitioner_id in physicianIdslist:
            query = """
            SELECT p.physician_id, p.email, p.first_name, p.last_name, rsl.total_fees, rsl.claims_processed, rsl.claims_pending, rsl.edit_eligibility_returns, rsl.interest,rsl.interest_claims_processed
            FROM physicians p, return_summary_lines rsl
            WHERE P.Physician_id = %s AND rsl.physician_id = p.physician_id
            """ % practitioner_id                  
            print query            
            cur.execute(query)            
            physician_email = [item[1] for item in cur.fetchall()][0]
            print physician_email
            cur.execute(query)            
            physician_preffered_name = [item[2]+' '+item[3] for item in cur.fetchall()][0] 
            cur.execute(query)
            total_fees = [item[4] for item in cur.fetchall()][0] 
            cur.execute(query)
            processed = [item[5] for item in cur.fetchall()][0]
            cur.execute(query)
            pending = [item[6] for item in cur.fetchall()][0]
            cur.execute(query)
            returns = [item[7] for item in cur.fetchall()][0]
            cur.execute(query)
            interest = [item[8] for item in cur.fetchall()][0]
            cur.execute(query)
            interest_claims = [item[9] for item in cur.fetchall()][0]
           
            message = """            
            Hello {0},
            The {1} reconciliation file has just been loaded into the system.
            Here's what was loaded:
            Total Fees: {2}
            Processed: {3}
            Pending: {4}
            Returns: {5}
            Interest: {6}
            Interest Claims: {7}  
            """.format(physician_preffered_name,'p4',total_fees,processed,pending,returns,interest,interest_claims)

            print message  
            print physician_email
            msg = MIMEText(message)
            msg['Subject'] = Subject

            try:
                smtpObj = smtplib.SMTP(mailServer,Port)
                smtpObj.login(mailServerUserName,mailServerPassword)       
                smtpObj.sendmail(sender,[physician_email], msg.as_string())         
                print "Successfully sent email"
            except SMTPException:
               print "Error: unable to send email"

    except MySQLdb.Error as errorMessage:
        sys.stderr.write(errorMessage)
        sys.exit(1)
                    
def main():
  if len(sys.argv) != 4:
    print 'usage: ./P4_processor.py MySQLPassword Inputfile SendE-mails(y/n)'
    sys.exit(1)

  global Password
  Password = sys.argv[1]
  filename = sys.argv[2]
  
  if sys.argv[3] not in ['y','n','Y','N']:
    print 'usage: ./P4_processor.py MySQLPassword Inputfile SendE-mails(y/n)'
    sys.exit(1)

  #Second argument for sending email 
  parse_file_data(filename,sys.argv[3])  
  sys.exit(1)

if __name__ == '__main__':
    main()
    # parse_file_data('P4-FEB 2014 MONTH-END.txt')
