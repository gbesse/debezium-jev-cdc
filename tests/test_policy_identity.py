import unittest,sqlite3
from cdc import process
class PolicyIdentityTests(unittest.TestCase):
 def test_same_version_changed_policy_rejudges(self):
  policy={'version':'1','primary_key':'id','text_field':'text','criteria':['yes','no'],'instructions':'first'};event={'op':'c','source':{'table':'t'},'after':{'id':1,'text':'source'}};calls=[]
  def judge(*_):calls.append(1);return {'choice':'yes','outcome':'yes','probability':.9}
  with sqlite3.connect(':memory:')as db:
   db.execute('create table decisions(source_key text primary key,fingerprint text)');a=process(event,db,policy,judge);self.assertIsNone(process(event,db,policy,judge));policy['instructions']='changed';b=process(event,db,policy,judge);self.assertEqual(len(calls),2);self.assertNotEqual(a['policy_sha256'],b['policy_sha256']);self.assertNotEqual(a['event_id'],b['event_id'])
