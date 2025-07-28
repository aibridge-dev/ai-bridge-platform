"""
Stripe payment service for AI Bridge platform
Handles subscriptions, project billing, and payment processing
"""
import stripe
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from src.models.user import User
from src.models.organization import Organization
from src.models.project import Project
from src.services.redis_service import redis_service
import json

class StripeService:
    def __init__(self):
        """Initialize Stripe service with API keys"""
        self.stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
        self.stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
        self.webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
        
        if self.stripe_secret_key:
            stripe.api_key = self.stripe_secret_key
        
        # Pricing configuration (per annotation)
        self.pricing_tiers = {
            'starter': {
                'price_per_annotation': 0.15,  # $0.15 per annotation
                'min_annotations': 1,
                'max_annotations': 1000,
                'features': ['Basic annotation tools', 'Standard quality control', 'Email support']
            },
            'professional': {
                'price_per_annotation': 0.12,  # $0.12 per annotation
                'min_annotations': 1001,
                'max_annotations': 10000,
                'features': ['Advanced annotation tools', 'Enhanced quality control', 'Priority support', 'API access']
            },
            'enterprise': {
                'price_per_annotation': 0.10,  # $0.10 per annotation
                'min_annotations': 10001,
                'max_annotations': None,
                'features': ['Custom annotation workflows', 'Dedicated quality team', '24/7 support', 'Custom integrations']
            }
        }
    
    def test_connection(self) -> bool:
        """Test Stripe API connection"""
        try:
            if not self.stripe_secret_key:
                return False
            
            # Test with a simple API call
            stripe.Account.retrieve()
            return True
        except Exception as e:
            print(f"Stripe connection test failed: {e}")
            return False
    
    def create_customer(self, user: User, organization: Organization = None) -> Optional[str]:
        """Create a Stripe customer for a user/organization"""
        try:
            customer_data = {
                'email': user.email,
                'name': user.full_name,
                'metadata': {
                    'user_id': str(user.id),
                    'platform': 'ai_bridge'
                }
            }
            
            if organization:
                customer_data['name'] = organization.name
                customer_data['metadata']['organization_id'] = str(organization.id)
            
            customer = stripe.Customer.create(**customer_data)
            
            # Cache customer ID
            cache_key = f"stripe_customer_{user.id}"
            redis_service.set(cache_key, customer.id, expire=86400)  # 24 hours
            
            return customer.id
            
        except Exception as e:
            print(f"Failed to create Stripe customer: {e}")
            return None
    
    def get_customer_id(self, user: User) -> Optional[str]:
        """Get or create Stripe customer ID for a user"""
        try:
            # Check cache first
            cache_key = f"stripe_customer_{user.id}"
            customer_id = redis_service.get(cache_key)
            
            if customer_id:
                return customer_id
            
            # Check if customer exists in Stripe
            customers = stripe.Customer.list(
                email=user.email,
                limit=1
            )
            
            if customers.data:
                customer_id = customers.data[0].id
                redis_service.set(cache_key, customer_id, expire=86400)
                return customer_id
            
            # Create new customer
            organization = Organization.query.get(user.organization_id) if user.organization_id else None
            return self.create_customer(user, organization)
            
        except Exception as e:
            print(f"Failed to get customer ID: {e}")
            return None
    
    def calculate_project_cost(self, annotation_count: int, custom_rate: float = None) -> Dict:
        """Calculate cost for a project based on annotation count"""
        try:
            if custom_rate:
                total_cost = annotation_count * custom_rate
                tier = 'custom'
                rate = custom_rate
            else:
                # Determine pricing tier
                if annotation_count <= 1000:
                    tier = 'starter'
                elif annotation_count <= 10000:
                    tier = 'professional'
                else:
                    tier = 'enterprise'
                
                rate = self.pricing_tiers[tier]['price_per_annotation']
                total_cost = annotation_count * rate
            
            # Apply volume discounts for large projects
            if annotation_count > 50000:
                discount_percentage = 0.15  # 15% discount
                discount_amount = total_cost * discount_percentage
                total_cost -= discount_amount
            elif annotation_count > 25000:
                discount_percentage = 0.10  # 10% discount
                discount_amount = total_cost * discount_percentage
                total_cost -= discount_amount
            elif annotation_count > 10000:
                discount_percentage = 0.05  # 5% discount
                discount_amount = total_cost * discount_percentage
                total_cost -= discount_amount
            else:
                discount_amount = 0
                discount_percentage = 0
            
            return {
                'annotation_count': annotation_count,
                'tier': tier,
                'rate_per_annotation': rate,
                'subtotal': annotation_count * rate,
                'discount_percentage': discount_percentage,
                'discount_amount': round(discount_amount, 2),
                'total_cost': round(total_cost, 2),
                'currency': 'usd'
            }
            
        except Exception as e:
            print(f"Failed to calculate project cost: {e}")
            return None
    
    def create_payment_intent(self, user: User, project: Project, annotation_count: int, 
                            custom_rate: float = None) -> Optional[Dict]:
        """Create a payment intent for a project"""
        try:
            customer_id = self.get_customer_id(user)
            if not customer_id:
                return None
            
            cost_breakdown = self.calculate_project_cost(annotation_count, custom_rate)
            if not cost_breakdown:
                return None
            
            # Convert to cents for Stripe
            amount_cents = int(cost_breakdown['total_cost'] * 100)
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                customer=customer_id,
                metadata={
                    'project_id': str(project.id),
                    'user_id': str(user.id),
                    'annotation_count': str(annotation_count),
                    'tier': cost_breakdown['tier'],
                    'platform': 'ai_bridge'
                },
                description=f"AI Bridge Data Labeling - Project: {project.name}"
            )
            
            return {
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': cost_breakdown['total_cost'],
                'currency': 'usd',
                'cost_breakdown': cost_breakdown
            }
            
        except Exception as e:
            print(f"Failed to create payment intent: {e}")
            return None
    
    def create_subscription(self, user: User, plan_type: str = 'professional') -> Optional[Dict]:
        """Create a monthly subscription for a user/organization"""
        try:
            customer_id = self.get_customer_id(user)
            if not customer_id:
                return None
            
            # Subscription pricing (monthly)
            subscription_plans = {
                'starter': {
                    'price': 99,  # $99/month
                    'included_annotations': 500,
                    'overage_rate': 0.15
                },
                'professional': {
                    'price': 299,  # $299/month
                    'included_annotations': 2000,
                    'overage_rate': 0.12
                },
                'enterprise': {
                    'price': 999,  # $999/month
                    'included_annotations': 10000,
                    'overage_rate': 0.10
                }
            }
            
            plan = subscription_plans.get(plan_type, subscription_plans['professional'])
            
            # Create price object
            price = stripe.Price.create(
                unit_amount=plan['price'] * 100,  # Convert to cents
                currency='usd',
                recurring={'interval': 'month'},
                product_data={
                    'name': f'AI Bridge {plan_type.title()} Plan',
                    'description': f'Monthly subscription with {plan["included_annotations"]} included annotations'
                }
            )
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price.id}],
                metadata={
                    'user_id': str(user.id),
                    'plan_type': plan_type,
                    'platform': 'ai_bridge'
                }
            )
            
            return {
                'subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'plan_type': plan_type,
                'monthly_cost': plan['price'],
                'included_annotations': plan['included_annotations']
            }
            
        except Exception as e:
            print(f"Failed to create subscription: {e}")
            return None
    
    def handle_webhook(self, payload: str, signature: str) -> bool:
        """Handle Stripe webhook events"""
        try:
            if not self.webhook_secret:
                return False
            
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            # Handle different event types
            if event['type'] == 'payment_intent.succeeded':
                self._handle_payment_success(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                self._handle_payment_failure(event['data']['object'])
            elif event['type'] == 'invoice.payment_succeeded':
                self._handle_subscription_payment(event['data']['object'])
            elif event['type'] == 'customer.subscription.deleted':
                self._handle_subscription_cancellation(event['data']['object'])
            
            return True
            
        except Exception as e:
            print(f"Webhook handling failed: {e}")
            return False
    
    def _handle_payment_success(self, payment_intent: Dict):
        """Handle successful payment"""
        try:
            project_id = payment_intent['metadata'].get('project_id')
            if project_id:
                project = Project.query.get(int(project_id))
                if project:
                    project.payment_status = 'paid'
                    project.status = 'active'
                    # Update project in database
                    # db.session.commit()
            
        except Exception as e:
            print(f"Failed to handle payment success: {e}")
    
    def _handle_payment_failure(self, payment_intent: Dict):
        """Handle failed payment"""
        try:
            project_id = payment_intent['metadata'].get('project_id')
            if project_id:
                project = Project.query.get(int(project_id))
                if project:
                    project.payment_status = 'failed'
                    # Update project in database
                    # db.session.commit()
            
        except Exception as e:
            print(f"Failed to handle payment failure: {e}")
    
    def _handle_subscription_payment(self, invoice: Dict):
        """Handle successful subscription payment"""
        try:
            customer_id = invoice['customer']
            # Update user subscription status
            # Implementation depends on your user model
            
        except Exception as e:
            print(f"Failed to handle subscription payment: {e}")
    
    def _handle_subscription_cancellation(self, subscription: Dict):
        """Handle subscription cancellation"""
        try:
            user_id = subscription['metadata'].get('user_id')
            if user_id:
                user = User.query.get(int(user_id))
                if user:
                    # Update user subscription status
                    # user.subscription_status = 'cancelled'
                    # db.session.commit()
                    pass
            
        except Exception as e:
            print(f"Failed to handle subscription cancellation: {e}")
    
    def get_pricing_info(self) -> Dict:
        """Get current pricing information"""
        return {
            'per_annotation_pricing': self.pricing_tiers,
            'subscription_plans': {
                'starter': {
                    'monthly_cost': 99,
                    'included_annotations': 500,
                    'overage_rate': 0.15,
                    'features': ['Basic annotation tools', 'Standard quality control', 'Email support']
                },
                'professional': {
                    'monthly_cost': 299,
                    'included_annotations': 2000,
                    'overage_rate': 0.12,
                    'features': ['Advanced annotation tools', 'Enhanced quality control', 'Priority support', 'API access']
                },
                'enterprise': {
                    'monthly_cost': 999,
                    'included_annotations': 10000,
                    'overage_rate': 0.10,
                    'features': ['Custom annotation workflows', 'Dedicated quality team', '24/7 support', 'Custom integrations']
                }
            },
            'volume_discounts': {
                '10,000+': '5% discount',
                '25,000+': '10% discount',
                '50,000+': '15% discount'
            }
        }

# Global instance
stripe_service = StripeService()

