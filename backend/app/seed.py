"""Demo data: 15 neighbors, each with 5 skills and 2 public needs, loaded at startup.

Demo accounts only. Every account uses DEMO_PASSWORD, so keep SEED_DEMO_DATA=false in production.
"""

import logging

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models.need import Need
from app.models.skill import Skill
from app.models.user import User

logger = logging.getLogger(__name__)

DEMO_PASSWORD = "1234567"

# username -> (skills as (name, details), needs as (title, description, priority, contact))
DEMO_PEOPLE: dict[str, tuple[list[tuple[str, str]], list[tuple[str, str, str, str]]]] = {
    "margaret_hayes": (
        [
            ("Baking", "Bread, pies, and cakes for families or church events"),
            ("Gardening", "Vegetable beds, weeding, and planting"),
            ("Canning", "Preserving jams, pickles, and tomatoes"),
            ("Knitting", "Scarves, blankets, and mending"),
            ("Pet sitting", "Dogs and cats while you are away"),
        ],
        [
            ("Ride to doctor appointments", "Need a driver to Clinton Memorial on Tuesdays", "high", "Call 555-0101"),
            ("Help moving a dresser", "Heavy dresser must go up a flight of stairs", "medium", "Porch at 12 Elm St"),
        ],
    ),
    "tom_becker": (
        [
            ("Lawn mowing", "Mowing, trimming, and leaf raking"),
            ("Carpentry", "Fence repair, shelves, and porch steps"),
            ("Driving", "Rides to appointments and the grocery store"),
            ("Snow removal", "Shoveling driveways and walks"),
            ("Moving help", "Lifting furniture and loading trucks"),
        ],
        [
            (
                "Tax preparation help",
                "Need help organizing paperwork for my return",
                "medium",
                "tom.becker@example.com",
            ),
            ("Bread and homemade meals", "Recovering from surgery and unable to cook", "high", "Call 555-0102"),
        ],
    ),
    "linda_ortiz": (
        [
            ("Tax preparation", "Individual returns and organizing paperwork"),
            ("Bookkeeping", "Household budgets and small business records"),
            ("Spanish tutoring", "Conversation and homework help"),
            ("Resume writing", "Job applications and interview practice"),
            ("Notary", "Notarizing forms and documents"),
        ],
        [
            ("Lawn mowing", "Cannot push a mower this summer", "medium", "Text 555-0103"),
            ("Computer repair", "Laptop is slow and shows pop-up warnings", "low", "Porch at 8 Oak Ave"),
        ],
    ),
    "james_whitfield": (
        [
            ("Computer repair", "Laptops, virus removal, and setup"),
            ("Tech tutoring", "Smartphones, email, and video calls for seniors"),
            ("Wi-Fi setup", "Routers, printers, and smart TVs"),
            ("Photography", "Family portraits and event photos"),
            ("Tax preparation", "Basic filing help"),
        ],
        [
            ("Garden help", "Weeding and planting a vegetable garden", "low", "Call 555-0104"),
            ("Ride to the airport", "Need a driver for an early morning flight next month", "medium", "Text 555-0104"),
        ],
    ),
    "patricia_nguyen": (
        [
            ("Child care", "Babysitting and after-school pickup"),
            ("Tutoring", "Math and reading for elementary students"),
            ("Cooking", "Meal prep and home-cooked dinners"),
            ("Sewing", "Hemming, repairs, and costumes"),
            ("Translation", "Vietnamese and English"),
        ],
        [
            ("Snow shoveling", "Elderly neighbor needs the driveway cleared", "high", "Call 555-0105"),
            ("Bicycle repair", "Flat tires and chain adjustment for two kids' bikes", "low", "Porch at 3 Mill St"),
        ],
    ),
    "robert_clark": (
        [
            ("Plumbing", "Leaky faucets, clogged drains, and toilets"),
            ("Electrical repair", "Outlets, switches, and light fixtures"),
            ("Painting", "Interior rooms and exterior trim"),
            ("Bicycle repair", "Tires, brakes, and tune-ups"),
            ("Tool lending", "Ladders, drills, and saws"),
        ],
        [
            ("Pet sitting", "Two dogs while I visit family for a week", "medium", "Text 555-0106"),
            ("Resume writing help", "Updating my resume after a layoff", "high", "robert.clark@example.com"),
        ],
    ),
    "susan_miller": (
        [
            ("Nursing care", "Blood pressure checks and medication reminders"),
            ("Elder companionship", "Visits, conversation, and walks"),
            ("Grocery shopping", "Errands and pharmacy pickups"),
            ("Meal delivery", "Hot meals to homebound neighbors"),
            ("Driving", "Rides to medical appointments"),
        ],
        [
            ("Plumbing repair", "Kitchen sink is leaking under the cabinet", "high", "Call 555-0107"),
            ("Painting a bedroom", "Need help painting before my grandchildren visit", "low", "Porch at 21 Walnut St"),
        ],
    ),
    "david_kim": (
        [
            ("Auto repair", "Oil changes, brakes, and battery swaps"),
            ("Welding", "Metal gates, rails, and trailer hitches"),
            ("Small engine repair", "Mowers, trimmers, and chainsaws"),
            ("Firewood splitting", "Cut and stacked firewood"),
            ("Hauling", "Truck and trailer for brush and debris"),
        ],
        [
            ("Babysitting", "Evening child care twice a month", "medium", "Text 555-0108"),
            ("Spanish tutoring", "Learning Spanish for work", "low", "david.kim@example.com"),
        ],
    ),
    "karen_johnson": (
        [
            ("Hair cutting", "Haircuts at home for seniors and kids"),
            ("Gardening", "Flower beds and container plants"),
            ("Quilting", "Custom quilts and repairs"),
            ("Event planning", "Church suppers and birthday parties"),
            ("Baking", "Cakes and cupcakes for celebrations"),
        ],
        [
            ("Tech tutoring for my phone", "Learning to use video calls with grandkids", "medium", "Call 555-0109"),
            ("Auto repair", "Car will not start and I cannot afford a shop", "high", "Call 555-0109"),
        ],
    ),
    "michael_adams": (
        [
            ("Legal paperwork help", "Wills, forms, and understanding notices"),
            ("Notary", "Notary public on weekends"),
            ("Bookkeeping", "Spreadsheets and bill organizing"),
            ("Driving", "Rides to court, work, or school"),
            ("Moving help", "Boxes, furniture, and loading"),
        ],
        [
            ("Firewood", "Need a cord of split firewood before winter", "medium", "Text 555-0110"),
            ("Haircut at home", "Mobility issues make salon trips difficult", "low", "Porch at 17 Pine St"),
        ],
    ),
    "angela_brooks": (
        [
            ("Mental health listening", "Peer support and a friendly ear"),
            ("Tutoring", "High school writing and college applications"),
            ("Resume writing", "Cover letters and interview coaching"),
            ("Yoga instruction", "Gentle yoga for seniors"),
            ("Child care", "Weekend babysitting"),
        ],
        [
            ("Electrical repair", "Porch light and outlet stopped working", "high", "Call 555-0111"),
            ("Moving help", "Moving to a new apartment on the first of the month", "medium", "Text 555-0111"),
        ],
    ),
    "frank_dawson": (
        [
            ("Home repair", "Roofing patches, gutters, and drywall"),
            ("Painting", "Houses, fences, and decks"),
            ("Snow removal", "Plowing driveways with a truck blade"),
            ("Gardening", "Raised beds and tilling"),
            ("Tool lending", "Power tools and a pressure washer"),
        ],
        [
            ("Meal delivery", "Wife is ill and we need hot dinners this month", "high", "Call 555-0112"),
            ("Photography for a reunion", "Family reunion photos in June", "low", "frank.dawson@example.com"),
        ],
    ),
    "helen_park": (
        [
            ("Cooking", "Korean and American meals for gatherings"),
            ("Translation", "Korean and English paperwork help"),
            ("Pet sitting", "Small pets and aquariums"),
            ("Knitting", "Hats and blankets for charity"),
            ("Child care", "After-school care"),
        ],
        [
            ("Computer help", "Printer will not connect to my Wi-Fi", "medium", "Text 555-0113"),
            ("Firewood splitting", "Have the logs but cannot split them", "low", "Porch at 5 Lake Rd"),
        ],
    ),
    "carlos_rivera": (
        [
            ("Landscaping", "Trimming hedges, planting trees, and mulch"),
            ("Concrete work", "Walkways, patios, and steps"),
            ("Spanish tutoring", "Native speaker for adults"),
            ("Moving help", "Strong crew for loading and unloading"),
            ("Hauling", "Dump runs and yard waste removal"),
        ],
        [
            ("Tax preparation", "First time filing with a small business income", "high", "Call 555-0114"),
            (
                "Bookkeeping help",
                "Need to track receipts for my landscaping work",
                "medium",
                "carlos.rivera@example.com",
            ),
        ],
    ),
    "betty_wallace": (
        [
            ("Sewing", "Alterations and clothing repair"),
            ("Quilting", "Hand-quilted gifts"),
            ("Canning", "Fruit preserves and relishes"),
            ("Elder companionship", "Card games and visits"),
            ("Cooking", "Southern-style home cooking"),
        ],
        [
            ("Painting my porch", "Porch railing needs scraping and a fresh coat", "medium", "Porch at 9 Church St"),
            ("Ride to church", "Need a ride each Sunday morning", "high", "Call 555-0115"),
        ],
    ),
}


def seed_demo_data(db: Session) -> int:
    """Create any missing demo neighbors with their skills and public needs.

    Existing usernames are left untouched, so running this repeatedly never duplicates data.
    Returns the number of users created.
    """
    existing = {u for (u,) in db.query(User.username).all()}
    hashed = hash_password(DEMO_PASSWORD)
    created = 0
    for username, (skills, needs) in DEMO_PEOPLE.items():
        if username in existing:
            continue
        user = User(username=username, email=f"{username}@example.com", hashed_password=hashed)
        db.add(user)
        db.flush()
        db.add_all(Skill(name=n, description=d, owner_id=user.id) for n, d in skills)
        db.add_all(
            Need(title=t, description=d, priority=p, contact=c, is_public=True, owner_id=user.id)
            for t, d, p, c in needs
        )
        created += 1
    db.commit()
    if created:
        logger.info("Seeded %d demo users", created)
    return created
