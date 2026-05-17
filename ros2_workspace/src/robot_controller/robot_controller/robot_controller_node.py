#!/usr/bin/env python3
"""
FILE: robot_controller_node.py
TYPE: ROS2 Node
PURPOSE: Bug2 navigation algorithm.

Bug2 is a classic reactive navigation algorithm used in real robots:
  1. Draw a straight M-Line from start to goal
  2. Drive along M-Line toward goal
  3. If obstacle hit, wall-follow (hug left wall) until M-Line is re-intercepted
     closer to the goal than where we left it
  4. Leave the wall, resume heading to goal
  5. Repeat until goal reached, then pick a new random goal

Only needs /scan (LiDAR) and /odom — no map required.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
import math
import random


# ── tunables ─────────────────────────────────────────────────────────────────
GOAL_TOLERANCE   = 0.30   # m  — close enough to goal
OBSTACLE_DIST    = 0.45   # m  — start wall-following
WALL_DIST        = 0.50   # m  — desired distance to keep from wall
WALL_KP          = 1.2    # proportional gain for wall distance control
LINEAR_SPEED     = 0.18   # m/s forward speed
MAX_ANGULAR      = 0.8    # rad/s
MLINE_TOLERANCE  = 0.12   # m  — how close to M-Line counts as "on it"
WORLD_BOUNDS     = 3.5    # m  — random goals drawn from [-B, B] x [-B, B]
# ─────────────────────────────────────────────────────────────────────────────


def angle_diff(a, b):
    """Signed difference a - b, wrapped to [-pi, pi]."""
    d = a - b
    while d >  math.pi: d -= 2 * math.pi
    while d < -math.pi: d += 2 * math.pi
    return d


def point_to_line_dist(px, py, x1, y1, x2, y2):
    """Perpendicular distance from point (px,py) to line through (x1,y1)-(x2,y2)."""
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    cx, cy = x1 + t * dx, y1 + t * dy
    return math.hypot(px - cx, py - cy)


def dist_to_goal(px, py, gx, gy):
    return math.hypot(gx - px, gy - py)


class State:
    GO_TO_GOAL   = "GO_TO_GOAL"
    WALL_FOLLOW  = "WALL_FOLLOW"


class RobotController(Node):

    def __init__(self):
        super().__init__('robot_controller')

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        self.create_subscription(Odometry,  '/odom', self.odom_cb, 10)
        self.create_timer(0.1, self.control_loop)

        # pose
        self.x = self.y = self.yaw = 0.0
        self.pose_ready = False

        # LiDAR
        self.front = self.left = self.front_left = self.front_right = float('inf')

        # Bug2 state
        self.state = State.GO_TO_GOAL

        # start & goal
        self.start_x = self.start_y = 0.0
        self.goal_x, self.goal_y = self._random_goal()
        self.hit_x = self.hit_y = 0.0   # where we first touched the obstacle
        self.hit_dist = float('inf')     # distance to goal at hit point

        self.get_logger().info(
            f'Bug2 controller started  goal→ ({self.goal_x:.2f}, {self.goal_y:.2f})')

    # ── helpers ──────────────────────────────────────────────────────────────

    def _random_goal(self):
        b = WORLD_BOUNDS
        return (round(random.uniform(-b, b), 2),
                round(random.uniform(-b, b), 2))

    def _new_goal(self):
        self.start_x, self.start_y = self.x, self.y
        self.goal_x, self.goal_y   = self._random_goal()
        self.state = State.GO_TO_GOAL
        self.get_logger().info(
            f'New goal → ({self.goal_x:.2f}, {self.goal_y:.2f})')

    def _on_mline(self):
        """True if robot is within MLINE_TOLERANCE of the M-Line (start→goal)."""
        return point_to_line_dist(
            self.x, self.y,
            self.start_x, self.start_y,
            self.goal_x,  self.goal_y
        ) < MLINE_TOLERANCE

    def _heading_to_goal(self):
        return math.atan2(self.goal_y - self.y, self.goal_x - self.x)

    def publish(self, linear, angular):
        cmd = Twist()
        cmd.linear.x  = float(max(-0.2, min(LINEAR_SPEED, linear)))
        cmd.angular.z = float(max(-MAX_ANGULAR, min(MAX_ANGULAR, angular)))
        self.cmd_pub.publish(cmd)

    # ── callbacks ────────────────────────────────────────────────────────────

    def scan_cb(self, msg):
        n = len(msg.ranges)

        def sec(a, b):
            i0, i1 = int(a / 360 * n), int(b / 360 * n)
            r = msg.ranges[i0:i1] if i0 < i1 else msg.ranges[i0:] + msg.ranges[:i1]
            v = [x for x in r if not math.isinf(x) and not math.isnan(x) and x > 0.01]
            return min(v) if v else float('inf')

        self.front       = sec(350, 10)
        self.front_left  = sec(10,  50)
        self.front_right = sec(310, 350)
        self.left        = sec(50,  130)

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.yaw = math.atan2(
            2*(q.w*q.z + q.x*q.y),
            1 - 2*(q.y*q.y + q.z*q.z))
        if not self.pose_ready:
            self.start_x, self.start_y = self.x, self.y
            self.pose_ready = True

    # ── control loop ─────────────────────────────────────────────────────────

    def control_loop(self):
        if not self.pose_ready:
            return

        # ── goal reached? ────────────────────────────────────────────────
        if dist_to_goal(self.x, self.y, self.goal_x, self.goal_y) < GOAL_TOLERANCE:
            self.get_logger().info(
                f'Goal ({self.goal_x:.2f},{self.goal_y:.2f}) reached!')
            self.publish(0.0, 0.0)
            self._new_goal()
            return

        if self.state == State.GO_TO_GOAL:
            self._go_to_goal()
        else:
            self._wall_follow()

    def _go_to_goal(self):
        """Head straight toward goal; switch to wall-follow if blocked."""
        if self.front < OBSTACLE_DIST:
            # record hit point
            self.hit_x, self.hit_y = self.x, self.y
            self.hit_dist = dist_to_goal(self.x, self.y, self.goal_x, self.goal_y)
            self.state = State.WALL_FOLLOW
            self.get_logger().warn(
                f'Obstacle hit at ({self.x:.2f},{self.y:.2f}) '
                f'dist_to_goal={self.hit_dist:.2f} → WALL_FOLLOW')
            return

        desired_yaw = self._heading_to_goal()
        err = angle_diff(desired_yaw, self.yaw)
        angular = max(-MAX_ANGULAR, min(MAX_ANGULAR, 2.0 * err))

        # slow down while turning sharply
        linear = LINEAR_SPEED * (1.0 - min(1.0, abs(err) / math.pi))
        self.publish(linear, angular)

    def _wall_follow(self):
        """
        Hug the left wall (left-hand rule) until we re-intercept the M-Line
        at a point closer to the goal than the hit point.
        """
        # Leave condition: on M-Line AND closer to goal AND not right at hit point
        on_line  = self._on_mline()
        d_goal   = dist_to_goal(self.x, self.y, self.goal_x, self.goal_y)
        past_hit = math.hypot(self.x - self.hit_x, self.y - self.hit_y) > 0.25

        if on_line and d_goal < self.hit_dist and past_hit:
            self.state = State.GO_TO_GOAL
            self.get_logger().info(
                f'M-Line re-intercepted at ({self.x:.2f},{self.y:.2f}) '
                f'dist={d_goal:.2f} < hit={self.hit_dist:.2f} → GO_TO_GOAL')
            return

        # Wall following: keep left wall at WALL_DIST
        # P-controller: error = desired_wall_dist - actual_left_dist
        wall_error = self.left - WALL_DIST
        angular = WALL_KP * wall_error   # positive error → too far from wall → turn left

        # avoid front obstacles while wall-following
        if self.front < OBSTACLE_DIST:
            # corner: turn right sharply
            angular = -MAX_ANGULAR
            self.publish(0.0, angular)
        elif self.front_left < OBSTACLE_DIST * 0.8:
            angular = -0.5
            self.publish(LINEAR_SPEED * 0.5, angular)
        else:
            self.publish(LINEAR_SPEED, angular)


def main(args=None):
    rclpy.init(args=args)
    node = RobotController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
