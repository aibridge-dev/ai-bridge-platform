"""
Payment routes for Stripe integration
Handles project billing, subscriptions, and payment processing
"""
from flask import Blueprint, request, jsonify, g
from src.models.user import User, UserRole
from src.models.project import Project
from src.models.organization import Organization
from src.routes.auth import token_required
from src.services.stripe_service import stripe_service
from src.services.redis_service import redis_service
import json

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/pricing', methods=['GET'])
def get_pricing():
    """Get current pricing information"""
    try:
        pricing_info = stripe_service.get_pricing_info()
        return jsonify(pricing_info), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch pricing: {str(e)}'}), 500

@payments_bp.route('/calculate-cost', methods=['POST'])
@token_required
def calculate_project_cost():
    """Calculate cost for a project based on annotation count"""
    try:
        data = request.get_json()
        annotation_count = data.get('annotation_count')
        custom_rate = data.get('custom_rate')
        
        if not annotation_count or annotation_count <= 0:
            return jsonify({'error': 'Valid annotation count is required'}), 400
        
        cost_breakdown = stripe_service.calculate_project_cost(
            annotation_count=annotation_count,
            custom_rate=custom_rate
        )
        
        if not cost_breakdown:
            return jsonify({'error': 'Failed to calculate cost'}), 500
        
        return jsonify(cost_breakdown), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to calculate cost: {str(e)}'}), 500

@payments_bp.route('/create-payment-intent', methods=['POST'])
@token_required
def create_payment_intent():
    """Create a payment intent for a project"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        annotation_count = data.get('annotation_count')
        custom_rate = data.get('custom_rate')
        
        if not project_id or not annotation_count:
            return jsonify({'error': 'Project ID and annotation count are required'}), 400
        
        # Get project and verify ownership
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Check if user has permission to pay for this project
        if (g.current_user.role not in [UserRole.ADMIN, UserRole.CLIENT_ADMIN] and 
            project.organization_id != g.current_user.organization_id):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        payment_intent_data = stripe_service.create_payment_intent(
            user=g.current_user,
            project=project,
            annotation_count=annotation_count,
            custom_rate=custom_rate
        )
        
        if not payment_intent_data:
            return jsonify({'error': 'Failed to create payment intent'}), 500
        
        return jsonify(payment_intent_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to create payment intent: {str(e)}'}), 500

@payments_bp.route('/create-subscription', methods=['POST'])
@token_required
def create_subscription():
    """Create a monthly subscription"""
    try:
        data = request.get_json()
        plan_type = data.get('plan_type', 'professional')
        
        if plan_type not in ['starter', 'professional', 'enterprise']:
            return jsonify({'error': 'Invalid plan type'}), 400
        
        # Only client admins and admins can create subscriptions
        if g.current_user.role not in [UserRole.ADMIN, UserRole.CLIENT_ADMIN]:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        subscription_data = stripe_service.create_subscription(
            user=g.current_user,
            plan_type=plan_type
        )
        
        if not subscription_data:
            return jsonify({'error': 'Failed to create subscription'}), 500
        
        return jsonify(subscription_data), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to create subscription: {str(e)}'}), 500

@payments_bp.route('/payment-methods', methods=['GET'])
@token_required
def get_payment_methods():
    """Get user's saved payment methods"""
    try:
        customer_id = stripe_service.get_customer_id(g.current_user)
        if not customer_id:
            return jsonify({'payment_methods': []}), 200
        
        import stripe
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type='card'
        )
        
        methods_data = []
        for pm in payment_methods.data:
            methods_data.append({
                'id': pm.id,
                'brand': pm.card.brand,
                'last4': pm.card.last4,
                'exp_month': pm.card.exp_month,
                'exp_year': pm.card.exp_year
            })
        
        return jsonify({'payment_methods': methods_data}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch payment methods: {str(e)}'}), 500

@payments_bp.route('/payment-history', methods=['GET'])
@token_required
def get_payment_history():
    """Get user's payment history"""
    try:
        customer_id = stripe_service.get_customer_id(g.current_user)
        if not customer_id:
            return jsonify({'payments': []}), 200
        
        import stripe
        charges = stripe.Charge.list(
            customer=customer_id,
            limit=50
        )
        
        payments_data = []
        for charge in charges.data:
            payments_data.append({
                'id': charge.id,
                'amount': charge.amount / 100,  # Convert from cents
                'currency': charge.currency,
                'status': charge.status,
                'description': charge.description,
                'created': charge.created,
                'receipt_url': charge.receipt_url
            })
        
        return jsonify({'payments': payments_data}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch payment history: {str(e)}'}), 500

@payments_bp.route('/subscription-status', methods=['GET'])
@token_required
def get_subscription_status():
    """Get user's current subscription status"""
    try:
        customer_id = stripe_service.get_customer_id(g.current_user)
        if not customer_id:
            return jsonify({'subscription': None}), 200
        
        import stripe
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status='active',
            limit=1
        )
        
        if not subscriptions.data:
            return jsonify({'subscription': None}), 200
        
        subscription = subscriptions.data[0]
        subscription_data = {
            'id': subscription.id,
            'status': subscription.status,
            'current_period_start': subscription.current_period_start,
            'current_period_end': subscription.current_period_end,
            'plan_type': subscription.metadata.get('plan_type', 'unknown'),
            'cancel_at_period_end': subscription.cancel_at_period_end
        }
        
        return jsonify({'subscription': subscription_data}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch subscription status: {str(e)}'}), 500

@payments_bp.route('/cancel-subscription', methods=['POST'])
@token_required
def cancel_subscription():
    """Cancel user's subscription"""
    try:
        data = request.get_json()
        subscription_id = data.get('subscription_id')
        cancel_immediately = data.get('cancel_immediately', False)
        
        if not subscription_id:
            return jsonify({'error': 'Subscription ID is required'}), 400
        
        # Only client admins and admins can cancel subscriptions
        if g.current_user.role not in [UserRole.ADMIN, UserRole.CLIENT_ADMIN]:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        import stripe
        if cancel_immediately:
            subscription = stripe.Subscription.delete(subscription_id)
        else:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        
        return jsonify({
            'message': 'Subscription cancelled successfully',
            'subscription': {
                'id': subscription.id,
                'status': subscription.status,
                'cancel_at_period_end': subscription.cancel_at_period_end
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to cancel subscription: {str(e)}'}), 500

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.get_data(as_text=True)
        signature = request.headers.get('Stripe-Signature')
        
        if not signature:
            return jsonify({'error': 'Missing signature'}), 400
        
        success = stripe_service.handle_webhook(payload, signature)
        
        if success:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'error': 'Webhook processing failed'}), 400
        
    except Exception as e:
        return jsonify({'error': f'Webhook error: {str(e)}'}), 400

@payments_bp.route('/publishable-key', methods=['GET'])
def get_publishable_key():
    """Get Stripe publishable key for frontend"""
    try:
        publishable_key = stripe_service.stripe_publishable_key
        if not publishable_key:
            return jsonify({'error': 'Stripe not configured'}), 500
        
        return jsonify({'publishable_key': publishable_key}), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get publishable key: {str(e)}'}), 500

@payments_bp.route('/usage-stats', methods=['GET'])
@token_required
def get_usage_stats():
    """Get user's usage statistics for billing"""
    try:
        # Get current month usage
        from datetime import datetime, timedelta
        from src.models.annotation import Annotation
        
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get annotations for current user's organization
        if g.current_user.organization_id:
            # Count annotations for the organization this month
            monthly_annotations = Annotation.query.join(
                Project, Annotation.project_id == Project.id
            ).filter(
                Project.organization_id == g.current_user.organization_id,
                Annotation.created_at >= current_month_start
            ).count()
        else:
            monthly_annotations = 0
        
        # Get subscription info
        customer_id = stripe_service.get_customer_id(g.current_user)
        subscription_info = None
        
        if customer_id:
            import stripe
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status='active',
                limit=1
            )
            
            if subscriptions.data:
                subscription = subscriptions.data[0]
                plan_type = subscription.metadata.get('plan_type', 'professional')
                
                # Get plan details
                pricing_info = stripe_service.get_pricing_info()
                plan_details = pricing_info['subscription_plans'].get(plan_type, {})
                
                included_annotations = plan_details.get('included_annotations', 0)
                overage_count = max(0, monthly_annotations - included_annotations)
                overage_cost = overage_count * plan_details.get('overage_rate', 0.12)
                
                subscription_info = {
                    'plan_type': plan_type,
                    'included_annotations': included_annotations,
                    'monthly_cost': plan_details.get('monthly_cost', 0),
                    'overage_rate': plan_details.get('overage_rate', 0.12)
                }
        
        usage_stats = {
            'current_month': {
                'annotations_used': monthly_annotations,
                'period_start': current_month_start.isoformat(),
                'period_end': (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            },
            'subscription': subscription_info,
            'overage': {
                'count': overage_count if subscription_info else 0,
                'cost': round(overage_cost, 2) if subscription_info else 0
            }
        }
        
        return jsonify(usage_stats), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch usage stats: {str(e)}'}), 500

