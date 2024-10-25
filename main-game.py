import pygame
import random
import pygame_gui
import math
from enum import Enum
from abc import ABC, abstractmethod

WIDTH, HEIGHT = 1200, 800
NUM_AGENTS = 2
FOOD_SIZE = 3
MAX_SPEED = 2
PLAYER_SPEED = 2
RUN_SPEED = 3
GUARD_PATROL_INTERVAL = 3000
CHASE_LOST_TIME = 3000
WALL_COLOR = (139, 69, 19)
FRAME_RATE = 0.1

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
manager = pygame_gui.UIManager((WIDTH, HEIGHT))
pygame.display.set_caption("Robbery Bob - Sneak Out Game")

background_img = pygame.image.load('assets/cement.jpg').convert()
orc_sprite_sheet = pygame.image.load('./assets/Orc.png').convert_alpha()

GUARD_SPRITE_SIZE = (100, 100)
guard_sprites = [pygame.transform.scale(orc_sprite_sheet.subsurface(pygame.Rect(i * GUARD_SPRITE_SIZE[0], 0, GUARD_SPRITE_SIZE[0], GUARD_SPRITE_SIZE[1])), (200, 200)) for i in range(6)]

walls = [
    pygame.Rect(50, 50, 1100, 20),
    pygame.Rect(50, 730, 1100, 20),
    pygame.Rect(50, 50, 20, 700),
    pygame.Rect(1130, 50, 20, 700),

    pygame.Rect(100, 100, 20, 200),
    pygame.Rect(150, 100, 300, 20),
    pygame.Rect(450, 100, 20, 150),
    pygame.Rect(100, 300, 150, 20),
    pygame.Rect(300, 150, 20, 250),
    pygame.Rect(500, 200, 200, 20),
    pygame.Rect(700, 200, 20, 300),
    pygame.Rect(500, 500, 300, 20),
    pygame.Rect(200, 500, 200, 20),
    pygame.Rect(800, 100, 20, 150),
    pygame.Rect(800, 400, 20, 250),
    pygame.Rect(850, 400, 150, 20),
    pygame.Rect(1000, 400, 20, 200),
    pygame.Rect(400, 600, 400, 20),
    pygame.Rect(900, 600, 200, 20)
]

# States------------
class AgentState(Enum):
    PATROL_STATE = 0
    CHASE_STATE = 1
    ATK_STATE = 2
#---------------------
class StateMachine():
    def __init__(self) -> None:
        self.states = {
            'patrol': PatrolState(),
            'chase': ChaseState(),
            'attack': AtkState(),
            'investigate': InvestigateState(),
            'alerting': AlertingState(),
            'idle': IdleState()
        }
        self.curret_state = 'patrol'
        print(f'Initialized with state: {self.curret_state}')

    def update(self, agent, target, noise_position):
        new_state = self.states[self.curret_state].update(agent, target, noise_position)
        if new_state:
            self.transition_to(agent, new_state)

    def transition_to(self, agent, new_state):
        print(f'Transitioning from {self.curret_state} to {new_state}')
        self.states[self.curret_state].exit(agent)
        self.curret_state = new_state
        self.states[self.curret_state].enter(agent)


class State(ABC):
    @abstractmethod
    def enter(self, agent):
        pass

    @abstractmethod
    def update(self, agent, target, noise_position):
        pass
    
    @abstractmethod
    def exit(self, agent):
        pass

class PatrolState(State):
    def enter(self, agent):
        agent.patrol_timer = pygame.time.get_ticks()
        agent.patrol_target = agent.patrol_points[0]
        agent.patrol_index = 0

    def update(self, agent, target, noise_position):
        current_time = pygame.time.get_ticks()
        if current_time - agent.patrol_timer > GUARD_PATROL_INTERVAL:
            agent.patrol_index = (agent.patrol_index + 1) % len(agent.patrol_points)
            agent.patrol_target = agent.patrol_points[agent.patrol_index]
            agent.patrol_timer = current_time

        if (agent.patrol_target - agent.position).length() > 5:
            direction = (agent.patrol_target - agent.position).normalize()
        else:
            direction = pygame.Vector2(0, 0)
        
        agent.velocity = direction * MAX_SPEED
        
        agent.position += agent.velocity

        # Collision
        for wall in walls:
            if wall.colliderect(pygame.Rect(agent.position.x - 5, agent.position.y - 5, 10, 10)):
                agent.position -= agent.velocity
                break


        if self.can_see_target(agent, target) and (target - agent.position).length() <= 150:
            print('Player detected, switching to chase state')
            agent.last_known_position = target
            return 'chase'
        if noise_position and (noise_position - agent.position).length() < 200:
            return 'investigate'

    def exit(self, agent):
        pass

    def find_path(self, agent, start, target):
        open_set = [start]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: (target - start).length()}
        while open_set:
            current = min(open_set, key=lambda point: f_score.get(point, float('inf')))
            if (current - target).length() < 10:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path
            open_set.remove(current)
            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + (neighbor - current).length()
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + (target - neighbor).length()
                    if neighbor not in open_set:
                        open_set.append(neighbor)
        return []

    def get_neighbors(self, position):
        directions = [
            pygame.Vector2(10, 0), pygame.Vector2(-10, 0),
            pygame.Vector2(0, 10), pygame.Vector2(0, -10)
        ]
        neighbors = []
        for direction in directions:
            neighbor = position + direction
            if not any(wall.collidepoint(neighbor.x, neighbor.y) for wall in walls):
                neighbors.append(neighbor)
        return neighbors

    def can_see_target(self, agent, target):
        direction = (target - agent.position).normalize()
        steps = int(min((target - agent.position).length(), 150) / 10)
        for i in range(steps):
            check_pos = agent.position + direction * (i * 10)
            if any(wall.collidepoint(check_pos.x, check_pos.y) for wall in walls):
                return False
        return True

class ChaseState(State):
    def enter(self, agent):
        agent.chase_timer = pygame.time.get_ticks()
        agent.velocity = pygame.Vector2(0, 0)

    def update(self, agent, target, noise_position):
        if (target - agent.position).length() > 5:
            direction = (target - agent.position).normalize() * (MAX_SPEED * 1.3)
        else:
            direction = pygame.Vector2(0, 0)
        agent.velocity = direction
        agent.position += agent.velocity

        for wall in walls:
            if wall.colliderect(pygame.Rect(agent.position.x - 5, agent.position.y - 5, 10, 10)):
                if abs(agent.velocity.x) > abs(agent.velocity.y):
                    agent.position.x -= agent.velocity.x
                else:
                    agent.position.y -= agent.velocity.y
                agent.velocity = pygame.Vector2(0, 0)
                break

        dist = (target - agent.position).length()
        if dist >= 150:
            current_time = pygame.time.get_ticks()
            if current_time - agent.chase_timer > CHASE_LOST_TIME:
                return 'investigate'
        if dist <= 10:
            return 'attack'

    def exit(self, agent):
        pass


class AtkState(State):
    def enter(self, agent):
        agent.velocity *= 0

    def update(self, agent, target, noise_position):
        dist = (target - agent.position).length()
        if dist > 10:
            return 'chase'

    def exit(self, agent):
        pass

class InvestigateState(State):
    def enter(self, agent):
        agent.investigate_timer = pygame.time.get_ticks()
        agent.investigate_target = agent.last_known_position if agent.last_known_position else agent.position

    def update(self, agent, target, noise_position):
        if agent.investigate_target and (agent.investigate_target - agent.position).length() > 0:
            direction = (agent.investigate_target - agent.position).normalize()
        else:
            direction = pygame.Vector2(0, 0)
        agent.velocity = direction * MAX_SPEED
        agent.position += agent.velocity

        for wall in walls:
            if wall.colliderect(pygame.Rect(agent.position.x - 5, agent.position.y - 5, 10, 10)):
                if abs(agent.velocity.x) > abs(agent.velocity.y):
                    agent.position.x -= agent.velocity.x
                else:
                    agent.position.y -= agent.velocity.y
                agent.velocity = pygame.Vector2(0, 0)
                break
        else:
            direction = pygame.Vector2(0, 0)
        agent.velocity = direction * MAX_SPEED
        agent.position += agent.velocity

        for wall in walls:
            if wall.collidepoint(agent.position.x, agent.position.y):
                agent.position -= agent.velocity
                break

        current_time = pygame.time.get_ticks()
        if current_time - agent.investigate_timer > GUARD_PATROL_INTERVAL:
            return 'patrol'

    def exit(self, agent):
        pass

class AlertingState(State):
    def enter(self, agent):
        pass

    def update(self, agent, target, noise_position):
        return 'patrol'

    def exit(self, agent):
        pass

class IdleState(State):
    def enter(self, agent):
        pass

    def update(self, agent, target, noise_position):
        pass

    def exit(self, agent):
        pass


class Agent:
    def __init__(self, patrol_points):
        self.patrol_timer = pygame.time.get_ticks()
        self.patrol_target = patrol_points[0]
        self.patrol_index = 0
        self.position = pygame.Vector2(patrol_points[0])
        self.velocity = pygame.Vector2(0, 0)
        self.patrol_points = patrol_points
        self.state_machine = StateMachine()
        self.last_known_position = None
        self.animation_index = 0

    def update(self, target, noise_position):
        if noise_position:
            self.last_known_position = noise_position
        self.state_machine.update(self, target, noise_position)

        self.animation_index = (self.animation_index + FRAME_RATE) % len(guard_sprites)

        if self.position.x > WIDTH:
            self.position.x = 0
        elif self.position.x < 0:
            self.position.x = WIDTH
        if self.position.y > HEIGHT:
            self.position.y = 0
        elif self.position.y < 0:
            self.position.y = HEIGHT

        return True

    def draw(self, screen):
        current_sprite = guard_sprites[int(self.animation_index)]
        if self.velocity.x < 0:
            current_sprite = pygame.transform.flip(current_sprite, True, False)
        screen.blit(current_sprite, (int(self.position.x) - GUARD_SPRITE_SIZE[0], int(self.position.y) - GUARD_SPRITE_SIZE[1]))
        cone_length = 150
        cone_angle = math.pi / 4
        direction = self.velocity.normalize() if self.velocity.length() > 0 else pygame.Vector2(1, 0)
        left_cone = direction.rotate_rad(-cone_angle) * cone_length
        right_cone = direction.rotate_rad(cone_angle) * cone_length

        if self.state_machine.curret_state == 'patrol':
            cone_color = (0, 255, 0, 100)  # Green
        elif self.state_machine.curret_state in ['alerting', 'investigate']:
            cone_color = (255, 255, 0, 100)  # Yellow
        elif self.state_machine.curret_state == 'chase':
            cone_color = (255, 0, 0, 100)  # Red

        vision_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(vision_surface, cone_color, [
            (self.position.x, self.position.y),
            (self.position.x + left_cone.x, self.position.y + left_cone.y),
            (self.position.x + right_cone.x, self.position.y + right_cone.y)
        ])
        screen.blit(vision_surface, (0, 0))


class Player:
    def __init__(self):
        self.position = pygame.Vector2(100, 100)
        self.speed = PLAYER_SPEED
        self.noise_position = None
        self.collectibles_collected = 0

    def update(self):
        keys = pygame.key.get_pressed()
        velocity = pygame.Vector2(0, 0)
        if keys[pygame.K_w]:
            velocity.y = -1
        if keys[pygame.K_s]:
            velocity.y = 1
        if keys[pygame.K_a]:
            velocity.x = -1
        if keys[pygame.K_d]:
            velocity.x = 1

        if keys[pygame.K_LSHIFT]:
            self.speed = RUN_SPEED
            self.noise_position = self.position.copy()
        else:
            self.speed = PLAYER_SPEED
            self.noise_position = None

        if velocity.length() > 0:
            velocity = velocity.normalize() * self.speed
            self.position += velocity

        for wall in walls:
            if wall.collidepoint(self.position.x, self.position.y):
                self.position -= velocity
                break

    def draw(self, screen):
        pygame.draw.circle(screen, (0, 0, 255), (int(self.position.x), int(self.position.y)), 10)


class Collectible:
    def __init__(self):
        self.position = pygame.Vector2(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50))

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 215, 0), (int(self.position.x), int(self.position.y)), 8)


def main():
    guard1_patrol_points = [pygame.Vector2(150, 150), pygame.Vector2(300, 150), pygame.Vector2(150, 400), pygame.Vector2(150, 700)]
    guard2_patrol_points = [pygame.Vector2(900, 150), pygame.Vector2(1050, 300), pygame.Vector2(900, 500), pygame.Vector2(1050, 700)]
    guard3_patrol_points = [pygame.Vector2(600, 100), pygame.Vector2(750, 200), pygame.Vector2(600, 400), pygame.Vector2(750, 600)]
    guard4_patrol_points = [pygame.Vector2(850, 150), pygame.Vector2(850, 500), pygame.Vector2(1000, 600)]
    guard5_patrol_points = [pygame.Vector2(100, 600), pygame.Vector2(1100, 600), pygame.Vector2(1050, 700), pygame.Vector2(50, 700)]
    guard6_patrol_points = [pygame.Vector2(600, 300), pygame.Vector2(800, 500), pygame.Vector2(400, 500), pygame.Vector2(600, 300)]
    agents = [Agent(guard1_patrol_points), Agent(guard2_patrol_points), Agent(guard3_patrol_points), Agent(guard5_patrol_points), Agent(guard6_patrol_points)]
    player = Player()
    collectible = Collectible()
    clock = pygame.time.Clock()

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0
        screen.blit(background_img, (0, 0))  # Draw the background
        manager.update(time_delta)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            manager.process_events(event)

        for wall in walls:
            pygame.draw.rect(screen, WALL_COLOR, wall)

        player.update()
        for agent in agents:
            agent.update(player.position, player.noise_position)

        if (player.position - collectible.position).length() < 15:
            player.collectibles_collected += 1
            collectible = Collectible()

        player.draw(screen)
        for agent in agents:
            agent.draw(screen)

        collectible.draw(screen)

        font = pygame.font.SysFont(None, 36)
        text_surface = font.render(f'Collectibles: {player.collectibles_collected}', True, (255, 255, 255))
        screen.blit(text_surface, (10, 10))

        manager.draw_ui(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
