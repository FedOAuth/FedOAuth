"""

"""

from openid.message import registerNamespaceAlias, \
     NamespaceAliasRegistrationError
from openid.extension import Extension
import logging

try:
    basestring #pylint:disable-msg=W0104
except NameError:
    # For Python 2.2
    basestring = (str, unicode) #pylint:disable-msg=W0622

__all__ = [
    'TeamsRequest',
    'TeamsResponse',
    'ns_uri',
    'supportsTeams',
    ]

# The namespace for this extension
ns_uri = 'http://ns.launchpad.net/2007/openid-teams'

try:
    registerNamespaceAlias(ns_uri, 'lp')
except NamespaceAliasRegistrationError, e:
    logging.exception('registerNamespaceAlias(%r, %r) failed: %s' % (ns_uri,
                                                               'teams', str(e),))

def supportsTeams(endpoint):
    """Does the given endpoint advertise support for team extension.

    @param endpoint: The endpoint object as returned by OpenID discovery
    @type endpoint: openid.consumer.discover.OpenIDEndpoint

    @returns: Whether an sreg type was advertised by the endpoint
    @rtype: bool
    """
    return endpoint.usesExtension(ns_uri)

class TeamsRequest(Extension):
    """An object to hold the state of a simple registration request.

    @ivar required: A list of the required fields in this simple
        registration request
    @type required: [str]

    @ivar optional: A list of the optional fields in this simple
        registration request
    @type optional: [str]

    @ivar policy_url: The policy URL that was provided with the request
    @type policy_url: str or NoneType

    @group Consumer: requestField, requestFields, getExtensionArgs, addToOpenIDRequest
    @group Server: fromOpenIDRequest, parseExtensionArgs
    """
    ns_uri = 'http://ns.launchpad.net/2007/openid-teams'
    ns_alias = 'lp'

    def __init__(self, requested=None,
                 sreg_ns_uri=ns_uri):
        """Initialize an empty simple registration request"""
        Extension.__init__(self)
        self.requested = []
        self.ns_uri = sreg_ns_uri

        if requested:
            self.requestTeams(requested)

    def requestedTeams(self):
        return self.requested

    def fromOpenIDRequest(cls, request):
        """Create a simple registration request that contains the
        fields that were requested in the OpenID request with the
        given arguments

        @param request: The OpenID request
        @type request: openid.server.CheckIDRequest

        @returns: The newly created simple registration request
        @rtype: C{L{SRegRequest}}
        """
        self = cls()

        # Since we're going to mess with namespace URI mapping, don't
        # mutate the object that was passed in.
        message = request.message.copy()

        args = message.getArgs(self.ns_uri)
        self.parseExtensionArgs(args)

        return self

    fromOpenIDRequest = classmethod(fromOpenIDRequest)

    def parseExtensionArgs(self, args, strict=False):
        """Parse the unqualified simple registration request
        parameters and add them to this object.

        This method is essentially the inverse of
        C{L{getExtensionArgs}}. This method restores the serialized simple
        registration request fields.

        If you are extracting arguments from a standard OpenID
        checkid_* request, you probably want to use C{L{fromOpenIDRequest}},
        which will extract the sreg namespace and arguments from the
        OpenID request. This method is intended for cases where the
        OpenID server needs more control over how the arguments are
        parsed than that method provides.

        >>> args = message.getArgs(ns_uri)
        >>> request.parseExtensionArgs(args)

        @param args: The unqualified simple registration arguments
        @type args: {str:str}

        @param strict: Whether requests with fields that are not
            defined in the simple registration specification should be
            tolerated (and ignored)
        @type strict: bool

        @returns: None; updates this object
        """
        items = args.get('query_membership')
        if items:
            for team_name in items.split(','):
                try:
                    self.requestTeam(team_name)
                except ValueError:
                    if strict:
                        raise

    def wereTeamsRequested(self):
        """Have any simple registration fields been requested?

        @rtype: bool
        """
        return bool(self.requested)

    def __requests__(self, team_name):
        """Was this field in the request?"""
        return team_name in self.requested

    def requestTeam(self, team_name, strict=False):
        """Request the specified field from the OpenID user

        @param field_name: the unqualified simple registration field name
        @type field_name: str

        @param required: whether the given field should be presented
            to the user as being a required to successfully complete
            the request

        @param strict: whether to raise an exception when a field is
            added to a request more than once

        @raise ValueError: when the field requested is not a simple
            registration field or strict is set and the field was
            requested more than once
        """
        if strict:
            if team_name in self.requested:
                raise ValueError('That team has already been requested')
        self.requested.append(team_name)

    def requestTeams(self, field_names, strict=False):
        """Add the given list of fields to the request

        @param field_names: The simple registration data fields to request
        @type field_names: [str]

        @param required: Whether these values should be presented to
            the user as required

        @param strict: whether to raise an exception when a field is
            added to a request more than once

        @raise ValueError: when a field requested is not a simple
            registration field or strict is set and a field was
            requested more than once
        """
        if isinstance(team_names, basestring):
            raise TypeError('Teams should be passed as a list of '
                            'strings (not %r)' % (type(field_names),))

        for team_name in team__names:
            self.requestTeam(team_name, strict=strict)

    def getExtensionArgs(self):
        """Get a dictionary of unqualified simple registration
        arguments representing this request.

        This method is essentially the inverse of
        C{L{parseExtensionArgs}}. This method serializes the simple
        registration request fields.

        @rtype: {str:str}
        """
        args = {}

        if self.requested:
            args['requested'] = ','.join(self.requested)

        return args

    def __repr__(self):
        return 'TeamsRequest. requestedTeams: %s' % self.requested

class TeamsResponse(Extension):
    """Represents the data returned in a simple registration response
    inside of an OpenID C{id_res} response. This object will be
    created by the OpenID server, added to the C{id_res} response
    object, and then extracted from the C{id_res} message by the
    Consumer.

    @ivar data: The simple registration data, keyed by the unqualified
        simple registration name of the field (i.e. nickname is keyed
        by C{'nickname'})

    @ivar ns_uri: The URI under which the simple registration data was
        stored in the response message.

    @group Server: extractResponse
    @group Consumer: fromSuccessResponse
    @group Read-only dictionary interface: keys, iterkeys, items, iteritems,
        __iter__, get, __getitem__, keys, has_key
    """

    ns_uri = 'http://ns.launchpad.net/2007/openid-teams'
    ns_alias = 'lp'

    def __init__(self, teams=None):
        Extension.__init__(self)
        if teams is None:
            self.teams = []
        else:
            self.teams = teams

    def extractResponse(cls, request, teams):
        """Take a C{L{SRegRequest}} and a dictionary of simple
        registration values and create a C{L{SRegResponse}}
        object containing that data.

        @param request: The simple registration request object
        @type request: SRegRequest

        @param data: The simple registration data for this
            response, as a dictionary from unqualified simple
            registration field name to string (unicode) value. For
            instance, the nickname should be stored under the key
            'nickname'.
        @type data: {str:str}

        @returns: a simple registration response object
        @rtype: SRegResponse
        """
        self = cls()
        for team in request.requestedTeams():
            if team in teams:
                self.teams.append(team)
        return self

    extractResponse = classmethod(extractResponse)

    def fromSuccessResponse(cls, success_response, signed_only=True):
        """Create a C{L{SRegResponse}} object from a successful OpenID
        library response
        (C{L{openid.consumer.consumer.SuccessResponse}}) response
        message

        @param success_response: A SuccessResponse from consumer.complete()
        @type success_response: C{L{openid.consumer.consumer.SuccessResponse}}

        @param signed_only: Whether to process only data that was
            signed in the id_res message from the server.
        @type signed_only: bool

        @rtype: SRegResponse
        @returns: A simple registration response containing the data
            that was supplied with the C{id_res} response.
        """
        self = cls()
        if signed_only:
            args = success_response.getSignedNS(self.ns_uri)
        else:
            args = success_response.message.getArgs(self.ns_uri)

        if not args:
            return None

        self.teams = args['is_member'].split(',')

        return self

    fromSuccessResponse = classmethod(fromSuccessResponse)

    def getExtensionArgs(self):
        """Get the fields to put in the simple registration namespace
        when adding them to an id_res message.

        @see: openid.extension
        """
        return {'is_member': ','.join(self.teams)}

    def __repr__(self):
        return 'TeamsResponse. Teams: %s' % self.teams

    # Read-only dictionary interface
    def get(self, field_name, default=None):
        if field_name != 'is_member':
            raise ValueError('teams invalid')
        return ','.join(self.teams)

    def items(self):
        return [','.join(self.teams)]

    def keys(self):
        return ['is_member']

    def has_key(self, key):
        return key == 'is_member'

    def __contains__(self, key):
        return key == 'is_member'
