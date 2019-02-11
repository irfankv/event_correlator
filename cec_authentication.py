import shlex
import subprocess
from subprocess import PIPE


class LDAPAuth:
    """LDAP Authentication Class

    This module is used for the places that require LDAP Authentication
    Using 'ldapwhoami' to verify if a user is authenticated
    """

    _default_dn = "-D cn='%s',ou=Employees,ou='Cisco Users',dc=cisco,dc=com"
    _default_host = "ldap://ds.cisco.com:389/"
    _default_tool = "ldapwhoami"
    _default_params = " -H {host} -x {dn} -w '%s' -e ppolicy -v"\
        .format(host=_default_host, dn=_default_dn)

    @staticmethod
    def auth(uid, passwd):
        """Verify if the user info is valid

        Args:
            uid (str): CEC user name
            passwd (str): CEC password

        Returns:
            True if the user is authenticated; else return False

        """
        command = LDAPAuth._default_tool + LDAPAuth._default_params % (uid, passwd)
        command_args = shlex.split(command)
        proc = subprocess.Popen(command_args, stdout=PIPE, stderr=PIPE)
        outs, errs = proc.communicate()
        outs = outs.decode("utf-8")

        if "Result: Success (0)" in outs and uid in outs:
            return True
        else:
            return False

if __name__ == '__main__':
    x = LDAPAuth()
    login_status = x.auth('nickcart', 'fakePassword')

    #if login_status:
    #    print "Success"
    #else:
    #    print "Fail"
