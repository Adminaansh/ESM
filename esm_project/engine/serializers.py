from rest_framework import serializers
from .models import Chain, ChainNode, ChainEdge
from studio.models import JobObject

class ChainNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChainNode
        fields = ['id', 'job', 'target', 'pos_x', 'pos_y']

class ChainEdgeSerializer(serializers.ModelSerializer):
    # We use Integers here so we can pass list indices (0, 1, 2...) from Postman
    source = serializers.IntegerField()
    target = serializers.IntegerField()

    class Meta:
        model = ChainEdge
        fields = ['id', 'source', 'target', 'condition']

    def to_representation(self, instance):
        return {
            'id': instance.id,
            'source': instance.source_id,
            'target': instance.target_id,
            'condition': instance.condition,
        }

class ChainSerializer(serializers.ModelSerializer):
    chain_id = serializers.IntegerField(source='chain_code', read_only=True)
    nodes = ChainNodeSerializer(many=True)
    edges = ChainEdgeSerializer(many=True)

    class Meta:
        model = Chain
        fields = ['id', 'chain_id', 'name', 'description', 'nodes', 'edges']

    def create(self, validated_data):
        nodes_data = validated_data.pop('nodes')
        edges_data = validated_data.pop('edges')

        chain = Chain.objects.create(**validated_data)

        created_nodes = []
        for node_data in nodes_data:
            node = ChainNode.objects.create(chain=chain, **node_data)
            created_nodes.append(node)

        for edge_data in edges_data:
            source_index = edge_data.pop('source')
            target_index = edge_data.pop('target')
            source_node = created_nodes[source_index]
            target_node = created_nodes[target_index]
            ChainEdge.objects.create(
                chain=chain,
                source=source_node,
                target=target_node,
                condition=edge_data.get('condition', 'SUCCESS')
            )

        return chain