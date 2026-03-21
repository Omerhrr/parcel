"""
Logistics Routes - Pickups, Dispatches, Deliveries
ParcelFlow - Multi-tenant Logistics Platform
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from app.utils.permissions import permission_required
import requests

logistics_bp = Blueprint('logistics', __name__)


def get_api_url():
    from flask import current_app
    return current_app.config.get('API_URL', 'http://localhost:8000/api')


def get_auth_headers():
    token_data = session.get('token_data', {})
    token = token_data.get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


# ============== PICKUPS ==============

@logistics_bp.route('/pickups')
@login_required
@permission_required('orders.view')
def list_pickups():
    """List pickups"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    scheduled_date = request.args.get('date', '')
    
    params = {'page': page, 'page_size': 20}
    if status:
        params['status'] = status
    if scheduled_date:
        params['scheduled_date'] = scheduled_date
    
    try:
        response = requests.get(
            f"{get_api_url()}/pickups",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    return render_template('logistics/pickups.html',
                         pickups=data.get('items', []),
                         pagination=data,
                         filters={'status': status, 'date': scheduled_date})


@logistics_bp.route('/pickups/<int:pickup_id>')
@login_required
@permission_required('orders.view')
def view_pickup(pickup_id):
    """View pickup details"""
    try:
        response = requests.get(
            f"{get_api_url()}/pickups/{pickup_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Pickup not found', 'error')
            return redirect(url_for('logistics.list_pickups'))
        pickup = response.json()
    except:
        flash('Error loading pickup', 'error')
        return redirect(url_for('logistics.list_pickups'))
    
    return render_template('logistics/pickup_detail.html', pickup=pickup)


@logistics_bp.route('/pickups/<int:pickup_id>/complete', methods=['POST'])
@login_required
@permission_required('deliveries.update')
def complete_pickup(pickup_id):
    """Complete a pickup"""
    try:
        response = requests.post(
            f"{get_api_url()}/pickups/{pickup_id}/complete",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Pickup completed successfully!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to complete pickup'), 'error')
    except:
        flash('Error completing pickup', 'error')
    
    return redirect(url_for('logistics.view_pickup', pickup_id=pickup_id))


@logistics_bp.route('/pickups/<int:pickup_id>/fail', methods=['POST'])
@login_required
@permission_required('deliveries.update')
def fail_pickup(pickup_id):
    """Mark pickup as failed"""
    reason = request.form.get('reason', '')
    
    try:
        response = requests.post(
            f"{get_api_url()}/pickups/{pickup_id}/fail",
            params={'reason': reason},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Pickup marked as failed', 'success')
        else:
            flash(response.json().get('detail', 'Failed to update pickup'), 'error')
    except:
        flash('Error updating pickup', 'error')
    
    return redirect(url_for('logistics.view_pickup', pickup_id=pickup_id))


# ============== DISPATCHES ==============

@logistics_bp.route('/dispatches')
@login_required
@permission_required('deliveries.view')
def list_dispatches():
    """List dispatches"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    agent_id = request.args.get('agent_id', '')
    
    params = {'page': page, 'page_size': 20}
    if status:
        params['status'] = status
    if agent_id:
        params['agent_id'] = agent_id
    
    try:
        response = requests.get(
            f"{get_api_url()}/dispatches",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    # Get agents for filter
    agents_response = requests.get(
        f"{get_api_url()}/agents",
        params={'page_size': 100},
        headers=get_auth_headers()
    )
    agents = agents_response.json().get('items', []) if agents_response.status_code == 200 else []
    
    return render_template('logistics/dispatches.html',
                         dispatches=data.get('items', []),
                         pagination=data,
                         agents=agents,
                         filters={'status': status, 'agent_id': agent_id})


@logistics_bp.route('/dispatches/create', methods=['GET', 'POST'])
@login_required
@permission_required('deliveries.create')
def create_dispatch():
    """Create/assign dispatch"""
    if request.method == 'POST':
        data = {
            'waybill_id': int(request.form.get('waybill_id')),
            'agent_id': int(request.form.get('agent_id')) if request.form.get('agent_id') else None,
            'vehicle_id': int(request.form.get('vehicle_id')) if request.form.get('vehicle_id') else None,
            'estimated_delivery': request.form.get('estimated_delivery'),
            'route_notes': request.form.get('route_notes'),
            'distance_km': float(request.form.get('distance_km')) if request.form.get('distance_km') else None
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/dispatches",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 201:
                flash('Dispatch created successfully!', 'success')
                return redirect(url_for('logistics.view_dispatch', dispatch_id=response.json()['id']))
            else:
                flash(response.json().get('detail', 'Failed to create dispatch'), 'error')
        except Exception as e:
            flash('Error creating dispatch', 'error')
    
    # Get waybill if provided
    waybill_id = request.args.get('waybill_id')
    waybill = None
    if waybill_id:
        try:
            response = requests.get(
                f"{get_api_url()}/waybills/{waybill_id}",
                headers=get_auth_headers()
            )
            if response.status_code == 200:
                waybill = response.json()
        except:
            pass
    
    # Get agents for assignment
    agents_response = requests.get(
        f"{get_api_url()}/agents",
        params={'page_size': 100, 'status': 'active'},
        headers=get_auth_headers()
    )
    agents = agents_response.json().get('items', []) if agents_response.status_code == 200 else []
    
    return render_template('logistics/dispatch_form.html', waybill=waybill, agents=agents)


@logistics_bp.route('/dispatches/<int:dispatch_id>')
@login_required
@permission_required('deliveries.view')
def view_dispatch(dispatch_id):
    """View dispatch details"""
    try:
        response = requests.get(
            f"{get_api_url()}/dispatches/{dispatch_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Dispatch not found', 'error')
            return redirect(url_for('logistics.list_dispatches'))
        dispatch = response.json()
    except:
        flash('Error loading dispatch', 'error')
        return redirect(url_for('logistics.list_dispatches'))
    
    return render_template('logistics/dispatch_detail.html', dispatch=dispatch)


@logistics_bp.route('/dispatches/<int:dispatch_id>/start', methods=['POST'])
@login_required
@permission_required('deliveries.update')
def start_dispatch(dispatch_id):
    """Start dispatch (mark as in transit)"""
    try:
        response = requests.post(
            f"{get_api_url()}/dispatches/{dispatch_id}/start",
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Dispatch started!', 'success')
        else:
            flash(response.json().get('detail', 'Failed to start dispatch'), 'error')
    except:
        flash('Error starting dispatch', 'error')
    
    return redirect(url_for('logistics.view_dispatch', dispatch_id=dispatch_id))


@logistics_bp.route('/dispatches/<int:dispatch_id>/attempt', methods=['POST'])
@login_required
@permission_required('deliveries.update')
def record_attempt(dispatch_id):
    """Record delivery attempt"""
    notes = request.form.get('notes', '')
    
    try:
        response = requests.post(
            f"{get_api_url()}/dispatches/{dispatch_id}/attempt",
            params={'notes': notes},
            headers=get_auth_headers()
        )
        if response.status_code == 200:
            flash('Attempt recorded', 'success')
        else:
            flash(response.json().get('detail', 'Failed to record attempt'), 'error')
    except:
        flash('Error recording attempt', 'error')
    
    return redirect(url_for('logistics.view_dispatch', dispatch_id=dispatch_id))


# ============== DELIVERIES ==============

@logistics_bp.route('/deliveries')
@login_required
@permission_required('deliveries.view')
def list_deliveries():
    """List delivery confirmations"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    params = {'page': page, 'page_size': 20}
    if status:
        params['status'] = status
    
    try:
        response = requests.get(
            f"{get_api_url()}/deliveries",
            params=params,
            headers=get_auth_headers()
        )
        data = response.json() if response.status_code == 200 else {'items': [], 'total': 0}
    except:
        data = {'items': [], 'total': 0}
    
    return render_template('logistics/deliveries.html',
                         deliveries=data.get('items', []),
                         pagination=data,
                         filters={'status': status})


@logistics_bp.route('/deliveries/create', methods=['GET', 'POST'])
@login_required
@permission_required('deliveries.create')
def confirm_delivery():
    """Confirm delivery"""
    if request.method == 'POST':
        data = {
            'waybill_id': int(request.form.get('waybill_id')),
            'status': request.form.get('status', 'delivered'),
            'receiver_name': request.form.get('receiver_name'),
            'receiver_relationship': request.form.get('receiver_relationship'),
            'receiver_id_type': request.form.get('receiver_id_type'),
            'receiver_id_number': request.form.get('receiver_id_number'),
            'receiver_signature_svg': request.form.get('receiver_signature_svg') or None,
            'cod_collected': request.form.get('cod_collected') == 'on',
            'cod_amount': float(request.form.get('cod_amount', 0)) if request.form.get('cod_amount') else None,
            'payment_method': request.form.get('payment_method'),
            'delivery_notes': request.form.get('delivery_notes')
        }
        
        try:
            response = requests.post(
                f"{get_api_url()}/deliveries",
                json=data,
                headers=get_auth_headers()
            )
            if response.status_code == 201:
                flash('Delivery confirmed successfully!', 'success')
                return redirect(url_for('logistics.view_delivery', delivery_id=response.json()['id']))
            else:
                flash(response.json().get('detail', 'Failed to confirm delivery'), 'error')
        except Exception as e:
            flash('Error confirming delivery', 'error')
    
    # Get waybill if provided
    waybill_id = request.args.get('waybill_id')
    waybill = None
    if waybill_id:
        try:
            response = requests.get(
                f"{get_api_url()}/waybills/{waybill_id}",
                headers=get_auth_headers()
            )
            if response.status_code == 200:
                waybill = response.json()
        except:
            pass
    
    return render_template('logistics/delivery_form.html', waybill=waybill)


@logistics_bp.route('/deliveries/<int:delivery_id>')
@login_required
@permission_required('deliveries.view')
def view_delivery(delivery_id):
    """View delivery confirmation"""
    try:
        response = requests.get(
            f"{get_api_url()}/deliveries/{delivery_id}",
            headers=get_auth_headers()
        )
        if response.status_code != 200:
            flash('Delivery not found', 'error')
            return redirect(url_for('logistics.list_deliveries'))
        delivery = response.json()
    except:
        flash('Error loading delivery', 'error')
        return redirect(url_for('logistics.list_deliveries'))
    
    return render_template('logistics/delivery_detail.html', delivery=delivery)


# ============== AGENT MAP ==============

@logistics_bp.route('/map')
@login_required
@permission_required('deliveries.view')
def agent_map():
    """Live agent map showing all active agents and their routes"""
    agents = []
    routes = []
    
    try:
        # Fetch agents with location data
        agents_response = requests.get(
            f"{get_api_url()}/agents/locations",
            headers=get_auth_headers()
        )
        if agents_response.status_code == 200:
            agents = agents_response.json()
    except Exception as e:
        pass
    
    try:
        # Fetch active dispatches/routes
        dispatches_response = requests.get(
            f"{get_api_url()}/dispatches",
            params={'status': 'in_transit', 'page_size': 100},
            headers=get_auth_headers()
        )
        if dispatches_response.status_code == 200:
            dispatches_data = dispatches_response.json()
            for dispatch in dispatches_data.get('items', []):
                waybill = dispatch.get('waybill', {})
                if waybill:
                    routes.append({
                        'id': dispatch.get('id'),
                        'pickup_lat': waybill.get('pickup_latitude'),
                        'pickup_lng': waybill.get('pickup_longitude'),
                        'pickup_address': waybill.get('sender_address', ''),
                        'delivery_lat': waybill.get('delivery_latitude'),
                        'delivery_lng': waybill.get('delivery_longitude'),
                        'delivery_address': waybill.get('receiver_address', ''),
                        'agent_name': dispatch.get('agent', {}).get('name', '') if dispatch.get('agent') else ''
                    })
    except Exception as e:
        pass
    
    # If no agents with locations, generate mock data for demo
    if not agents:
        import random
        # Generate mock agent locations (centered around Nairobi, Kenya)
        mock_locations = [
            (-1.286389, 36.817223),  # Nairobi CBD
            (-1.265600, 36.799650),  # Westlands
            (-1.300000, 36.850000),  # Industrial Area
            (-1.270000, 36.830000),  # Kilimani
            (-1.290000, 36.790000),  # Parklands
        ]
        
        mock_agents_response = requests.get(
            f"{get_api_url()}/agents",
            params={'page_size': 10},
            headers=get_auth_headers()
        )
        
        if mock_agents_response.status_code == 200:
            mock_agents_data = mock_agents_response.json()
            for i, agent in enumerate(mock_agents_data.get('items', [])[:5]):
                lat, lng = mock_locations[i % len(mock_locations)]
                # Add small random offset for visibility
                lat += random.uniform(-0.01, 0.01)
                lng += random.uniform(-0.01, 0.01)
                
                agents.append({
                    'id': agent.get('id'),
                    'name': agent.get('name'),
                    'phone': agent.get('phone'),
                    'status': agent.get('status'),
                    'total_deliveries': agent.get('total_deliveries', 0),
                    'rating': float(agent.get('rating', 0)) if agent.get('rating') else 0,
                    'current_latitude': str(lat),
                    'current_longitude': str(lng),
                    'current_dispatch': None
                })
    
    return render_template('logistics/agent_map.html', agents=agents, routes=routes)
