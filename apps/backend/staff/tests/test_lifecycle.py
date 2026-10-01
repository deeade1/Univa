from django.test import SimpleTestCase

from staff.models import StaffMember

class StaffEmploymentTransitionContractTests(SimpleTestCase):
    def test_transition_matrix(self):
        status = StaffMember.EmploymentStatus

        expected = {
            status.PENDING: {
                status.ACTIVE,
            },
            status.ACTIVE: {
                status.ON_LEAVE,
                status.SUSPENDED,
                status.RESIGNED,
                status.TERMINATED,
            },
            status.ON_LEAVE: {
                status.ACTIVE,
                status.SUSPENDED,
                status.RESIGNED,
                status.TERMINATED,
            },
            status.SUSPENDED: {
                status.ACTIVE,
                status.RESIGNED,
                status.TERMINATED,
            },
            status.RESIGNED: set(),
            status.TERMINATED: set(),
        }

        self.assertEqual(
            set(expected),
            {choice[0] for choice in status.choices},
        )

        self.assertEqual(
            expected[status.PENDING],
            {status.ACTIVE},
        )

        self.assertEqual(
            expected[status.ACTIVE],
            {
                status.ON_LEAVE,
                status.SUSPENDED,
                status.RESIGNED,
                status.TERMINATED,
            },
        )

        self.assertEqual(
            expected[status.ON_LEAVE],
            {
                status.ACTIVE,
                status.SUSPENDED,
                status.RESIGNED,
                status.TERMINATED,
            },
        )

        self.assertEqual(
            expected[status.SUSPENDED],
            {
                status.ACTIVE,
                status.RESIGNED,
                status.TERMINATED,
            },
        )

        self.assertEqual(expected[status.RESIGNED], set())
        self.assertEqual(expected[status.TERMINATED], set())

    def test_pending_cannot_skip_to_terminal_or_suspended_states(self):
        status = StaffMember.EmploymentStatus

        allowed = {status.ACTIVE}

        self.assertNotIn(status.ON_LEAVE, allowed)
        self.assertNotIn(status.SUSPENDED, allowed)
        self.assertNotIn(status.RESIGNED, allowed)
        self.assertNotIn(status.TERMINATED, allowed)

    def test_resigned_cannot_be_reactivated(self):
        status = StaffMember.EmploymentStatus

        allowed = set()

        self.assertNotIn(status.ACTIVE, allowed)

    def test_terminated_cannot_be_reactivated(self):
        status = StaffMember.EmploymentStatus

        allowed = set()

        self.assertNotIn(status.ACTIVE, allowed)

