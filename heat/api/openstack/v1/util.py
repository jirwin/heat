# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from webob import exc
from functools import wraps

from heat.common import identifier


def tenant_local(handler):
    '''
    Decorator for a handler method that sets the correct tenant_id in the
    request context.
    '''
    @wraps(handler)
    def handle_stack_method(controller, req, tenant_id, **kwargs):
        req.context.tenant_id = tenant_id
        return handler(controller, req, **kwargs)

    return handle_stack_method


def identified_stack(handler):
    '''
    Decorator for a handler method that passes a stack identifier in place of
    the various path components.
    '''
    @tenant_local
    @wraps(handler)
    def handle_stack_method(controller, req, stack_name, stack_id, **kwargs):
        stack_identity = identifier.HeatIdentifier(req.context.tenant_id,
                                                   stack_name,
                                                   stack_id)
        return handler(controller, req, dict(stack_identity), **kwargs)

    return handle_stack_method


def identified_resource(handler):
    '''
    Decorator for a handler method that passes a resource identifier in place
    of the various path components.
    '''
    @identified_stack
    @wraps(handler)
    def handle_stack_method(controller, stack_identity,
                            resource_name, **kwargs):
        resource_identity = identifier.ResourceIdentifier(stack_identity,
                                                          resource_name)
        return handler(controller, req, dict(resource_identity), **kwargs)

    return handle_stack_method


def make_url(req, identity):
    '''Return the URL for the supplied identity dictionary.'''
    try:
        stack_identity = identifier.HeatIdentifier(**identity)
    except ValueError:
        err_reason = _('Invalid Stack address')
        raise exc.HTTPInternalServerError(explanation=err_reason)

    return req.relative_url(stack_identity.url_path(), True)


def make_link(req, identity, relationship='self'):
    '''Return a link structure for the supplied identity dictionary.'''
    return {'href': make_url(req, identity), 'rel': relationship}


def remote_error(ex, force_exists=False):
    """
    Map rpc_common.RemoteError exceptions returned by the engine
    to webob exceptions which can be used to return
    properly formatted error responses.
    """

    client_error = exc.HTTPBadRequest if force_exists else exc.HTTPNotFound
    error_map = {
        'AttributeError': client_error,
        'ValueError': client_error,
        'StackNotFound': exc.HTTPNotFound,
        'ResourceNotFound': exc.HTTPNotFound,
        'ResourceNotAvailable': exc.HTTPNotFound,
        'PhysicalResourceNotFound': exc.HTTPNotFound,
        'InvalidTenant': exc.HTTPForbidden,
        'StackExists': exc.HTTPConflict,
    }

    Exc = error_map.get(ex.exc_type, exc.HTTPInternalServerError)

    raise Exc(explanation=str(ex))
