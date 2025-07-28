#!/usr/bin/env python3
"""
Create subscription plans for AI Bridge platform
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.main_simple import app, db, SubscriptionPlan

def create_subscription_plans():
    with app.app_context():
        # Create all tables first
        db.create_all()
        
        # Clear existing plans if any
        try:
            SubscriptionPlan.query.delete()
        except:
            pass  # Table might not exist yet
        
        # Create subscription plans
        plans = [
            {
                'name': 'Starter',
                'price': 29.99,
                'features': 'Up to 5 projects,1000 annotations per month,Basic support,Standard quality control',
                'max_projects': 5,
                'max_annotations': 1000
            },
            {
                'name': 'Professional',
                'price': 99.99,
                'features': 'Up to 25 projects,10000 annotations per month,Priority support,Advanced quality control,Custom workflows,API access',
                'max_projects': 25,
                'max_annotations': 10000
            },
            {
                'name': 'Enterprise',
                'price': 299.99,
                'features': 'Unlimited projects,Unlimited annotations,24/7 dedicated support,Advanced analytics,Custom integrations,White-label options,SLA guarantee',
                'max_projects': 999999,
                'max_annotations': 999999
            }
        ]
        
        for plan_data in plans:
            plan = SubscriptionPlan(
                name=plan_data['name'],
                price=plan_data['price'],
                features=plan_data['features'],
                max_projects=plan_data['max_projects'],
                max_annotations=plan_data['max_annotations']
            )
            db.session.add(plan)
        
        db.session.commit()
        print("✅ Subscription plans created successfully!")
        
        # Print plans
        plans = SubscriptionPlan.query.all()
        for plan in plans:
            print(f"\n📋 {plan.name} Plan:")
            print(f"   Price: ${plan.price}/month")
            print(f"   Max Projects: {plan.max_projects}")
            print(f"   Max Annotations: {plan.max_annotations}")
            print(f"   Features: {plan.features}")

if __name__ == '__main__':
    create_subscription_plans()

